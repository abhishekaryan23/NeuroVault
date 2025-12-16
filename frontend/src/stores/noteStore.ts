import { create } from 'zustand';
import {
    createNoteApiNotesPost,
    getTimelineApiTimelineGet,
    searchNotesApiSearchGet,
    getSummaryApiSummaryGet,
    refreshSummaryApiSummaryRefreshPost,
    uploadFileApiUploadPost
} from '../client';
import type {
    NoteResponse,
    SummaryResponse,
    SearchResult
} from '../client';

interface NoteState {
    // State
    notes: NoteResponse[];
    searchResults: SearchResult[];
    searchQuery: string;
    isVoiceSearch: boolean;
    summary: SummaryResponse | null;
    isLoading: boolean;
    error: string | null;

    // Actions
    setSearchQuery: (query: string, isVoice?: boolean) => void;
    setSearchResults: (results: SearchResult[]) => void;
    fetchTimeline: (skip?: number, limit?: number) => Promise<void>;
    createNote: (content: string, mediaType?: 'text' | 'image' | 'voice' | 'file', tags?: string[], filePath?: string) => Promise<void>;
    searchNotes: (query: string, mediaType?: 'image' | 'text' | 'voice' | 'pdf') => Promise<void>;
    fetchSummary: () => Promise<void>;
    refreshSummary: () => Promise<void>;
    uploadFile: (file: File) => Promise<{ filePath: string, extractedContent: string, mediaType: string, tags: string[] }>;
    deleteNote: (id: number) => Promise<void>;

    // Tasks
    tasks: (NoteResponse & { is_task?: boolean; is_completed?: boolean; category?: string; origin_note_id?: number | null; event_at?: string | null; })[];
    fetchTasks: () => Promise<void>;
    toggleTaskCompletion: (id: number, completed: boolean) => Promise<void>;
}

export const useNoteStore = create<NoteState>((set, get) => ({
    notes: [],
    searchResults: [],
    searchQuery: '',
    isVoiceSearch: false,
    summary: null,
    isLoading: false,
    error: null,

    setSearchQuery: (query, isVoice = false) => set({ searchQuery: query, isVoiceSearch: isVoice }),
    setSearchResults: (results) => set({ searchResults: results }),

    fetchTimeline: async (skip = 0, limit = 20) => {
        set({ isLoading: true, error: null });
        try {
            const { data, error } = await getTimelineApiTimelineGet({ query: { skip, limit } });
            if (error) throw new Error("Failed to fetch timeline");
            if (data) set({ notes: data });
        } catch (err) {
            set({ error: (err as Error).message });
        } finally {
            set({ isLoading: false });
        }
    },

    createNote: async (content, mediaType = 'text', tags = [], filePath) => {
        set({ isLoading: true, error: null });
        try {
            // Intelligent Routing: 
            // If it's a pure Text Dump (no file attachment), route via Agent to support Events/Tasks extraction.
            if (mediaType === 'text' && !filePath) {
                const formData = new FormData();
                formData.append('text', content);
                formData.append('speak', 'false'); // Don't speak back for text dumps

                const res = await fetch('http://localhost:8000/api/voice/command', {
                    method: 'POST',
                    body: formData
                });
                if (!res.ok) throw new Error("Agent processing failed");
                // We don't need the response text/audio for now, just the side effect (Note creation)
            } else {
                // Legacy/Simple path for Files/Images or specific types
                const { error } = await createNoteApiNotesPost({
                    body: {
                        content,
                        media_type: mediaType as any,
                        tags,
                        file_path: filePath
                    }
                });
                if (error) throw new Error("Failed to create note");
            }

            // Always refresh timeline
            await get().fetchTimeline();
        } catch (err) {
            set({ error: (err as Error).message });
        } finally {
            set({ isLoading: false });
        }
    },

    searchNotes: async (query, mediaType) => {
        if (!query && !mediaType) {
            set({ searchResults: [] });
            return;
        }
        // Clear previous results immediately for better UX
        if (query) {
            set({ searchResults: [] });
        }

        set({ isLoading: true, error: null });
        try {
            // Manually constructing query due to strict typing of generated client
            // or we cast it if client isn't updated? 
            // The generated client expects specific obj. Let's force it or use raw fetch if needed.
            // Actually, best to just pass it if the client definition allows extra props? No it doesn't.
            // I'll assume I update client types or just cast keys.
            // But wait, the previous step didn't update types.gen.ts for the search endpoint.
            // I should update types.gen.ts first to be clean.
            // But for speed, I can just append it to the URL manually using axios if I wanted?
            // Actually, let's just use `searchNotesApiSearchGet` with a cast. Valid TS fix.

            // Dynamic limit: 5 for search, 50 for browsing/homepage
            const limit = query ? 5 : 50;
            const queryObj: any = { q: query, limit: limit };
            if (mediaType) queryObj.media_type = mediaType;

            const { data, error } = await searchNotesApiSearchGet({ query: queryObj });
            if (error) throw new Error("Search failed");
            if (data) set({ searchResults: data as SearchResult[] });
        } catch (err) {
            set({ error: (err as Error).message });
        } finally {
            set({ isLoading: false });
        }
    },

    fetchSummary: async () => {
        set({ isLoading: true, error: null });
        try {
            const { data, error } = await getSummaryApiSummaryGet();
            if (error) {
                set({ summary: null });
            } else if (data) {
                set({ summary: data as SummaryResponse });
            }
        } catch (err) {
            set({ summary: null });
        } finally {
            set({ isLoading: false });
        }
    },

    refreshSummary: async () => {
        set({ isLoading: true, error: null });
        try {
            const { data, error, response } = await refreshSummaryApiSummaryRefreshPost();

            if (response.status === 404) {
                // Graceful handling for no content
                set({ summary: null, error: null });
                return;
            }

            if (error) throw new Error("Summary refresh failed");
            if (data) set({ summary: data as SummaryResponse });
        } catch (err) {
            set({ error: (err as Error).message });
        } finally {
            set({ isLoading: false });
        }
    },

    uploadFile: async (file) => {
        try {
            const { data, error } = await uploadFileApiUploadPost({
                body: {
                    file: file as any
                }
            });
            if (error || !data) throw new Error("Upload failed");

            return {
                filePath: (data as any).file_path,
                extractedContent: (data as any).extracted_content,
                mediaType: (data as any).media_type,
                tags: (data as any).tags || []
            };
        } catch (err) {
            throw err;
        }
    },

    deleteNote: async (id: number) => {
        // Optimistic update
        const previousNotes = get().notes;
        set({ notes: previousNotes.filter(n => n.id !== id) });

        try {
            const { deleteNoteApiNotesNoteIdDelete } = await import('../client');
            const { error } = await deleteNoteApiNotesNoteIdDelete({ path: { note_id: id } });
            if (error) throw new Error("Failed to delete note");
        } catch (err) {
            // Revert on failure
            set({ notes: previousNotes, error: "Failed to delete note" });
        }
    },

    // --- Task / Todo Actions ---
    tasks: [],

    fetchTasks: async () => {
        // fetching only incomplete tasks by default
        try {
            const res = await fetch('http://localhost:8000/api/tasks?include_completed=true');
            if (!res.ok) throw new Error("Failed to fetch tasks");
            const data = await res.json();
            set({ tasks: data });
        } catch (err) {
            console.error(err);
        }
    },

    toggleTaskCompletion: async (id: number, completed: boolean) => {
        // Optimistic update
        const previousTasks = get().tasks;
        set({
            tasks: previousTasks.map(t =>
                t.id === id ? { ...t, is_completed: completed, updated_at: new Date().toISOString() } : t
            )
        });

        try {
            const res = await fetch(`http://localhost:8000/api/notes/${id}/complete?completed=${completed}`, {
                method: 'PATCH'
            });
            if (!res.ok) throw new Error("Failed to update task");
        } catch (err) {
            // Revert
            set({ tasks: previousTasks });
        }
    }
}));
