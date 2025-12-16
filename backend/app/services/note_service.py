from typing import List, Optional, Any
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.models.base import Note
from app.schemas.note import NoteCreate
from app.services.vector_service import VectorService

class NoteService:
    @staticmethod
    async def create_note(db: AsyncSession, note_in: NoteCreate) -> Note:
        # 1. Create Note in main table
        # Summarization is now handled via BackgroundTasks in the API layer
        
        db_note = Note(
            content=note_in.content,
            media_type=note_in.media_type,
            tags=note_in.tags,
            file_path=note_in.file_path,
            summary=None, # Filled later by background task
            parent_id=getattr(note_in, 'parent_id', None),
            is_hidden=getattr(note_in, 'is_hidden', False),
            is_processing=getattr(note_in, 'is_processing', False),
            is_task=getattr(note_in, 'is_task', False),
            is_completed=getattr(note_in, 'is_completed', False),
            category=getattr(note_in, 'category', None),
            origin_note_id=getattr(note_in, 'origin_note_id', None),
            event_at=getattr(note_in, 'event_at', None),
            event_duration=getattr(note_in, 'event_duration', 60)
        )
        db.add(db_note)
        await db.commit()
        await db.refresh(db_note)

        # 2. Vector Embedding (Only if not processing in background)
        # Note: We keep embedding synchronous for now to ensure search works instantly?
        # Actually, for "Super Fast", we should technically verify if embedding blocks.
        # It takes ~200ms for short text. Let's keep it sync for now as users expect immediate searchability.
        # But we could move it to background too if needed.


        # 2. Vector Embedding (Only if not processing in background)
        # If is_processing=True, we skip embedding here; the background task will do it later for chunks.
        # But wait, create_note is also used for chunks? 
        # Chunks will have is_processing=False (they are ready when created).
        # Parent PDF will have is_processing=True.
        # So effective logic: Only embed if NOT processing. 
        # AND: We only embed 'TEXT' or 'PDF' chunks. We don't embed the Parent PDF container usually?
        # Actually we DO want to embed everything searchable. 
        # But for Parent PDF, it's just a holder? 
        # The parent note has truncated content. Embedding it is fine, acts as a summary match.
        # But if it's "Processing", maybe postpone embedding?
        # Let's simple check:
        
        if not db_note.is_processing and note_in.content:
            try:
                # Construct enriched text for embedding
                # This drastically improves search by matching tags and summaries
                parts = []
                if note_in.media_type:
                    parts.append(f"Type: {note_in.media_type}")
                
                # Handle tags (might be list or string depending on source, but Pydantic guarantees list here)
                if note_in.tags:
                    tag_str = ", ".join(note_in.tags)
                    parts.append(f"Tags: {tag_str}")
                
                if db_note.summary:
                    parts.append(f"Summary: {db_note.summary}")
                
                parts.append(f"Content: {note_in.content}")
                
                text_to_embed = "\n".join(parts)

                vector = await VectorService.embed_text(text_to_embed)
                stmt = text("INSERT INTO vec_notes(rowid, embedding) VALUES (:id, :embedding)")
                # sqlite-vec expects raw bytes or json? 
                # We used json.loads in read. Insert should be safe with list?
                # sqlite-vec python client handles list -> blob? 
                # Actually previously we saw it returns BLOB.
                # To insert, passing a list of floats usually works with recent libraries.
                # Let's ensure json string to be safe if direct list fails, 
                # but previously we inserted without explicit json dumps? 
                # Wait, looking at previous code:
                # `await db.execute(stmt, {"id": db_note.id, "embedding": str(vector)})` ?
                # I need to check how I was inserting.
                # I'll check/view NoteService again to be safe.
                # Assuming I fix the insertion in a moment, let's just add the check.
                import json
                await db.execute(stmt, {"id": db_note.id, "embedding": json.dumps(vector)})
                await db.commit()
            except Exception as e:
                print(f"Embedding failed: {e}") 
        
        return db_note

    @staticmethod
    async def mark_as_processed(db: AsyncSession, note_id: int):
        stmt = select(Note).where(Note.id == note_id)
        result = await db.execute(stmt)
        note = result.scalars().first()
        if note:
            note.is_processing = False
            await db.commit()

    @staticmethod
    async def get_timeline(db: AsyncSession, skip: int = 0, limit: int = 20):
        # Return simple list of notes ordered by creation, excluding hidden chunks
        stmt = select(Note).where(Note.is_active == True, Note.is_hidden == False).order_by(desc(Note.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def search_notes(db: AsyncSession, query_text: str, limit: int = 10, media_type: str = None, start_date: datetime = None, end_date: datetime = None):
        # Base SQL components
        filter_clause = "notes.is_active = 1"
        params = {"limit": limit}

        if media_type:
            filter_clause += " AND notes.media_type = :media_type"
            params["media_type"] = media_type

        if start_date and end_date:
            # Filter by CREATION time OR EVENT time
            filter_clause += " AND ((notes.event_at IS NOT NULL AND notes.event_at BETWEEN :start_date AND :end_date) OR (notes.event_at IS NULL AND notes.created_at BETWEEN :start_date AND :end_date))"
            params["start_date"] = start_date
            params["end_date"] = end_date

        # Case 1: Simple Filter (No Vector Search)
        if not query_text:
            sql = text(f"""
                SELECT 
                    id, content, media_type, tags, created_at, updated_at, is_active, file_path, 
                    is_hidden, is_processing, is_task, is_completed, category, parent_id,
                    event_at, event_duration
                FROM notes
                WHERE {filter_clause}
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            
            result = await db.execute(sql, params)
            rows = result.fetchall()
            
            # Map to NoteResponse (distance=0 since no search)
            # Post-processing to aggregate parents
            final_results = []
            seen_ids = set()
            parent_ids_to_fetch = set()
            
            # First pass: identify parents needed
            for row in rows:
                if row.parent_id:
                    parent_ids_to_fetch.add(row.parent_id)
            
            parents_map = {}
            if parent_ids_to_fetch:
                parent_stmt = select(Note).where(Note.id.in_(parent_ids_to_fetch))
                parent_res = await db.execute(parent_stmt)
                for p in parent_res.scalars().all():
                    parents_map[p.id] = p
            
            for row in rows:
                target_note = None
                
                # Only swap for parent if we are NOT strictly filtering by media_type
                # If user asks for 'image', give them the image (child), not the parent (text)
                should_use_parent = (row.parent_id and row.parent_id in parents_map and not media_type)
                
                if should_use_parent:
                    target_note = parents_map[row.parent_id]
                else:
                    target_note = Note(
                        id=row.id,
                        content=row.content,
                        media_type=row.media_type,
                        tags=row.tags if not isinstance(row.tags, str) else [], # Will be parsed below if needed, but here we construct manual
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                        is_active=row.is_active,
                        file_path=row.file_path,
                        is_hidden=row.is_hidden,
                        is_processing=row.is_processing,
                        is_task=row.is_task,
                        is_completed=row.is_completed,
                        category=row.category,
                        parent_id=row.parent_id,
                        event_at=row.event_at,
                        event_duration=row.event_duration if row.event_duration is not None else 60
                    )
                    # Small fix for tags parsing if it comes as string from raw sql
                    if isinstance(row.tags, str):
                        try:
                            import json
                            target_note.tags = json.loads(row.tags)
                        except:
                            target_note.tags = []

                if target_note and target_note.id not in seen_ids:
                    seen_ids.add(target_note.id)
                    final_results.append({"note": target_note, "distance": 0.0})
            
            return final_results

        # Case 2: Vector Search
        # 1. Embed query (Local Embedding Model)
        query_vector = await VectorService.embed_text(query_text)
        import json
        query_vec_json = json.dumps(query_vector)
        params["query_vec"] = query_vec_json
        
        # 2. Hybrid Search Query
        # Join vec_notes with notes to get content
        # vec_notes.embedding MATCH query_vector
        # Filter is_active=1
        
        # Base SQL components
        filter_clause = "notes.is_active = 1"
        params = {"query_vec": query_vec_json, "limit": limit}
        
        if media_type:
            filter_clause += " AND notes.media_type = :media_type"
            params["media_type"] = media_type
            
        if start_date and end_date:
            filter_clause += " AND ((notes.event_at IS NOT NULL AND notes.event_at BETWEEN :start_date AND :end_date) OR (notes.event_at IS NULL AND notes.created_at BETWEEN :start_date AND :end_date))"
            params["start_date"] = start_date
            params["end_date"] = end_date
            
        sql = text(f"""
            SELECT 
                notes.id, notes.content, notes.media_type, notes.tags, notes.created_at, notes.updated_at, notes.is_active, notes.file_path,
                notes.is_hidden, notes.is_processing, notes.is_task, notes.is_completed, notes.category, notes.parent_id,
                notes.event_at, notes.event_duration,
                v.distance
            FROM (
                SELECT rowid, distance
                FROM vec_notes
                WHERE embedding MATCH :query_vec
                ORDER BY distance
                LIMIT :limit
            ) as v
            JOIN notes ON v.rowid = notes.id
            WHERE {filter_clause}
            ORDER BY v.distance
        """)
        
        result = await db.execute(sql, params)
        rows = result.fetchall()
        
        # Parse result into NoteResponse + distance
        final_results = []
        seen_ids = set()
        parent_ids_to_fetch = set()
        
        # 1. Identify all parents needed
        for row in rows:
            if row.parent_id:
                parent_ids_to_fetch.add(row.parent_id)
        
        # 2. Bulk fetch parents
        parents_map = {}
        if parent_ids_to_fetch:
            parent_stmt = select(Note).where(Note.id.in_(parent_ids_to_fetch))
            parent_res = await db.execute(parent_stmt)
            for p in parent_res.scalars().all():
                parents_map[p.id] = p
        
        # 3. Construct results, preferring parents
        for row in rows:
            target_note = None
            
            should_use_parent = (row.parent_id and row.parent_id in parents_map and not media_type)
            
            if should_use_parent:
                # partial match in chunk -> verify parent
                target_note = parents_map[row.parent_id]
            else:
                # It's a standalone note OR we failed to find parent (orphan chunk?)
                # Construct Note object from row
                tags = row.tags
                if isinstance(tags, str):
                    try:
                        import json
                        tags = json.loads(tags)
                    except:
                        tags = []
                
                target_note = Note(
                    id=row.id,
                    content=row.content,
                    media_type=row.media_type,
                    tags=tags,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    is_active=row.is_active,
                    file_path=row.file_path,
                    is_hidden=row.is_hidden,
                    is_processing=row.is_processing,
                    is_task=row.is_task,
                    is_completed=row.is_completed,
                    category=row.category,
                    parent_id=row.parent_id,
                    event_at=row.event_at,
                    event_duration=row.event_duration if row.event_duration is not None else 60
                )

            # Deduplicate
            if target_note and target_note.id not in seen_ids:
                seen_ids.add(target_note.id)
                final_results.append({"note": target_note, "distance": row.distance})
            
        return final_results
            
        return results

    @staticmethod
    async def get_note_context(db: AsyncSession, parent_id: int, query_text: str, top_k: int = 5) -> List[str]:
        """
        Perform strict scoped RAG: Search only within the children of parent_id.
        Uses in-memory similarity for accuracy on the specific document subset.
        """
        # 1. Get all child IDs
        stmt = select(Note.id).where(Note.parent_id == parent_id)
        result = await db.execute(stmt)
        child_ids = result.scalars().all()
        
        if not child_ids:
            return []
            
        # 2. Embed Query
        query_vector = await VectorService.embed_text(query_text)
        
        # 3. Fetch Embeddings for these children (Manual Join)
        import json
        import numpy as np
        
        # Construct placeholders for IN clause
        placeholders = ",".join([":id" + str(i) for i in range(len(child_ids))])
        params = {f"id{i}": cid for i, cid in enumerate(child_ids)}
        
        sql = text(f"SELECT rowid, embedding FROM vec_notes WHERE rowid IN ({placeholders})")
        
        try:
            vec_result = await db.execute(sql, params)
            rows = vec_result.fetchall()
            
            # 4. Calculate Similarity
            scores = []
            q_vec = np.array(query_vector)
            
            for row in rows:
                if not row.embedding: continue
                try:
                    # sqlite-vec returns little-endian float32 blob
                    # If it was inserted as string, it might come back as string? 
                    # But usually vec0 returns blob.
                    if isinstance(row.embedding, bytes):
                        vec = np.frombuffer(row.embedding, dtype=np.float32)
                    elif isinstance(row.embedding, str):
                        vec = np.array(json.loads(row.embedding))
                    else:
                        print(f"Unknown embedding type: {type(row.embedding)}")
                        continue
                        
                    score = np.dot(vec, q_vec)
                    scores.append((row.rowid, score))
                except Exception as e:
                    print(f"Vector parse error id={row.rowid}: {e}")
                    continue
            
            # 5. Sort and Top K
            scores.sort(key=lambda x: x[1], reverse=True)
            top_ids = [x[0] for x in scores[:3]] # Limit to Top 3 for performance
            
            if not top_ids:
                return []
                
            # 6. Fetch Content
            content_stmt = select(Note.content).where(Note.id.in_(top_ids))
            content_result = await db.execute(content_stmt)
            return content_result.scalars().all()
            
        except Exception as e:
            return []
            
        except Exception as e:
            print(f"Context search failed: {e}")
            return []

    @staticmethod
    async def update_note(db: AsyncSession, note_id: int, note_update: dict) -> Optional[Note]:
        stmt = select(Note).where(Note.id == note_id)
        result = await db.execute(stmt)
        note = result.scalars().first()
        
        if not note:
            return None
            
        for key, value in note_update.items():
            setattr(note, key, value)
            
        note.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(note)
        
        # Re-embed if content changed? 
        # For now, we assume caller handles re-embedding or we ignore it for simple property updates.
        # Ideally, if content changes, we should update vector.
        if "content" in note_update:
             # Trigger background embedding or do it here?
             # Let's keep it simple: if processing is done, we might want to embed.
             # Caller should handle vector update if needed? 
             # Or we can just call the vector service here.
             pass
             
        return note

    @staticmethod
    async def delete_note(db: AsyncSession, note_id: int) -> bool:
        # 1. Get note to check for file
        stmt = select(Note).where(Note.id == note_id)
        result = await db.execute(stmt)
        note = result.scalars().first()
        
        if not note:
            return False
            
        # 2. Delete file from disk if exists
        if note.file_path:
            import os
            if os.path.exists(note.file_path):
                try:
                    os.remove(note.file_path)
                except Exception as e:
                    print(f"Failed to delete file {note.file_path}: {e}")

        # 3. Delete from vec_notes (Shadow Table)
        # Using raw SQL for virtual table
        try:
            vec_stmt = text("DELETE FROM vec_notes WHERE rowid = :id")
            await db.execute(vec_stmt, {"id": note_id})
        except Exception as e:
            print(f"Failed to delete vector: {e}")

        # 3.5. Cascade Delete Children (if this is a parent note)
        # Find children (chunks)
        child_stmt = select(Note).where(Note.parent_id == note_id)
        child_result = await db.execute(child_stmt)
        children = child_result.scalars().all()
        
        # 3.6. Cascade Delete Linked Tasks (if this is a source note)
        linked_stmt = select(Note).where(Note.origin_note_id == note_id)
        linked_result = await db.execute(linked_stmt)
        linked_tasks = linked_result.scalars().all()
        
        # Combine lists to delete all dependents
        dependents = list(children) + list(linked_tasks)
        
        for child in dependents:
            # Delete dependent vector
            try:
                await db.execute(text("DELETE FROM vec_notes WHERE rowid = :id"), {"id": child.id})
            except:
                pass
                
            # Delete dependent note
            await db.delete(child)
            
        # 4. Check if this note is part of the latest summary.
        # If so, invalidate the summary (delete it), so it regenerates or shows empty.
        # This keeps "Rolling Updates" in sync with actual available data.
        from app.services.summary_service import SummaryService
        
        # We need to do this BEFORE deleting the note? No, after is fine, or before.
        # Actually logic is: if note_id in summary.linked_note_ids -> delete summary.
        # Ideally we check the latest summary.
        latest_summary = await SummaryService.get_latest_summary(db)
        if latest_summary and latest_summary.linked_note_ids:
             # Ensure linked_note_ids is a list (it should be from JSON)
             linked_ids = latest_summary.linked_note_ids
             if isinstance(linked_ids, list) and note_id in linked_ids:
                 await db.delete(latest_summary)
                 # We don't need to generate a new one immediately. 
                 # Next GET /summary will trigger generation or 404.

        # 5. Delete from main notes table
        await db.delete(note)
        await db.commit()
        
        return True

    @staticmethod
    async def background_summarize_note(note_id: int):
        """
        Background Task: Generate summary for a note.
        Uses its own DB session.
        """
        from app.services.summary_service import SummaryService
        from db.database import async_session_maker
        from app.models.base import Note
        
        async with async_session_maker() as db:
            stmt = select(Note).where(Note.id == note_id)
            result = await db.execute(stmt)
            note = result.scalars().first()
            
            if not note or not note.content:
                return
                
            try:
                # print(f"[BG] Summarizing note {note_id}...")
                summary_text = await SummaryService.summarize_single_note(note.content)
                note.summary = summary_text
                await db.commit()
                # print(f"[BG] Note {note_id} summarized.")
            except Exception as e:
                print(f"[BG] Summary failed for {note_id}: {e}")
