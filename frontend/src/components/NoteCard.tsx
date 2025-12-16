import type { NoteResponse } from '../client';
import { PhotoIcon, MicrophoneIcon, DocumentTextIcon, TrashIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline';
import { useNoteStore } from '../stores/noteStore';
import { useSettingsStore } from '../stores/settingsStore';
import { useState, useEffect } from 'react';
import { AgentChatModal } from './AgentChatModal';

interface NoteCardProps {
    note: NoteResponse;
}

export const NoteCard = ({ note }: NoteCardProps) => {
    const { deleteNote } = useNoteStore();
    const { timezone } = useSettingsStore();

    // Ensure date is treated as UTC if naive
    const rawDate = note.created_at;
    const dateStr = rawDate.endsWith('Z') || rawDate.includes('+') ? rawDate : `${rawDate}Z`;

    const date = new Date(dateStr).toLocaleString('en-US', {
        timeZone: timezone,
        dateStyle: 'medium',
        timeStyle: 'short'
    });

    const [expanded, setExpanded] = useState(false);
    const [isChatOpen, setIsChatOpen] = useState(false);

    // Local state to track full note data (for polling updates)
    const [currentNote, setCurrentNote] = useState(note);
    const [isProcessing, setIsProcessing] = useState(note.is_processing);

    // Derived values from currentNote (not prop note)
    const summary = currentNote.summary;
    const isPdf = currentNote.media_type === 'pdf' || currentNote.file_path?.endsWith('.pdf');
    const isImage = currentNote.media_type === 'image';
    const fileUrl = currentNote.file_path ? `http://localhost:8000/files/${currentNote.file_path.replace(/^dumps\//, '')}` : '';
    const fileName = currentNote.file_path ? currentNote.file_path.split('/').pop() : 'Document';

    // Poll for status update if processing
    useEffect(() => {
        let interval: any;
        // Skip polling for optimistic/temp IDs (timestamps)
        const isTempId = typeof note.id === 'number' && note.id > 1000000000000;

        if (isProcessing && !isTempId) {
            interval = setInterval(async () => {
                try {
                    const res = await fetch(`http://localhost:8000/api/notes/${note.id}`);
                    if (res.ok) {
                        const updatedNote = await res.json();
                        // Update local state with fresh data (summary, etc.)
                        setCurrentNote(updatedNote);

                        if (!updatedNote.is_processing) {
                            setIsProcessing(false);
                        }
                    } else if (res.status === 404) {
                        // Note might have been deleted or ID changed
                        setIsProcessing(false);
                    }
                } catch (e) {
                    console.error("Polling failed", e);
                }
            }, 3000);
        }
        return () => clearInterval(interval);
    }, [isProcessing, note.id]);

    const handleDelete = async () => {
        if (window.confirm('Are you sure you want to delete this note permanently?')) {
            await deleteNote(currentNote.id);
        }
    };

    return (
        <div className="bg-graphite p-5 rounded-2xl border border-white/5 mb-4 hover:border-banana/30 transition-all shadow-sm group relative">
            {/* Delete Button */}
            <button
                onClick={handleDelete}
                className="absolute top-4 right-4 text-ash-gray hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity p-1 z-10"
                title="Delete dump"
            >
                <TrashIcon className="h-4 w-4" />
            </button>

            {/* Header: Date + Optional Icon for Voice/Text/Event */}
            <div className="flex items-center gap-2 mb-3 opacity-60 flex-wrap">
                {currentNote.media_type === 'voice' && <MicrophoneIcon className="h-3 w-3 text-neural-purple" />}
                {currentNote.media_type === 'text' && <DocumentTextIcon className="h-3 w-3 text-ash-gray" />}

                <span className="text-[10px] text-ash-gray font-mono uppercase tracking-wider" title="Created At">
                    {date}
                </span>

                {/* Event Time Badge */}
                {note.event_at && (
                    <span className="flex items-center gap-1 text-[10px] font-bold text-banana bg-banana/10 px-2 py-0.5 rounded-full border border-banana/20 uppercase tracking-wide">
                        <span className="w-1.5 h-1.5 rounded-full bg-banana animate-pulse"></span>
                        Event: {new Date(note.event_at).toLocaleString('en-US', {
                            timeZone: timezone,
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric',
                            hour: 'numeric',
                            minute: '2-digit'
                        })}
                    </span>
                )}
            </div>

            {/* Content: Hide text summary/content if it is an image */}
            {!isImage && (
                <div className="prose prose-sm max-w-none text-gray-300 whitespace-pre-wrap leading-relaxed">
                    {summary && !expanded ? (
                        <div>
                            <p className="italic text-gray-400 border-l-2 border-banana/30 pl-3 mb-2">{summary}</p>
                            <button
                                onClick={() => setExpanded(true)}
                                className="text-xs text-banana hover:underline font-bold top-1 relative"
                            >
                                {fileName} &rarr;
                            </button>
                        </div>
                    ) : (
                        <div>
                            {!expanded && !summary && currentNote.content.length > 500 ? (
                                <div>
                                    {currentNote.content.substring(0, 500)}...
                                    <button
                                        onClick={() => setExpanded(true)}
                                        className="block mt-2 text-xs text-banana hover:underline font-bold"
                                    >
                                        Read more
                                    </button>
                                </div>
                            ) : (
                                <div>
                                    {currentNote.content}
                                    {(summary || currentNote.content.length > 500) && expanded && (
                                        <button
                                            onClick={() => setExpanded(false)}
                                            className="block mt-2 text-xs text-ash-gray hover:text-white"
                                        >
                                            Show Less
                                        </button>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Attachments */}
            {note.file_path && (
                <div className="mt-3">
                    {/* Audio Player */}
                    {(note.media_type === 'voice' || note.file_path?.endsWith('.wav')) && (
                        <div className="w-full bg-black/20 rounded-xl p-3 border border-white/5">
                            <audio
                                controls
                                src={fileUrl}
                                className="w-full h-8 [&::-webkit-media-controls-panel]:bg-transparent [&::-webkit-media-controls-enclosure]:bg-transparent"
                            />
                        </div>
                    )}

                    {/* Image Preview - Click to open */}
                    {isImage && (
                        <a
                            href={fileUrl}
                            target="_blank"
                            rel="noreferrer"
                            className="block group/image overflow-hidden rounded-xl border border-white/10 relative max-w-md"
                        >
                            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover/image:opacity-100 transition-opacity flex items-center justify-center z-10">
                                <span className="text-white text-xs font-bold uppercase tracking-wider flex items-center gap-2 bg-black/50 px-3 py-1 rounded-full border border-white/20 backdrop-blur-sm">
                                    <PhotoIcon className="h-4 w-4" />
                                    Open Image
                                </span>
                            </div>
                            <img
                                src={fileUrl}
                                alt="Note attachment"
                                className="w-full h-auto object-cover transform group-hover/image:scale-105 transition-transform duration-500"
                                loading="lazy"
                            />
                        </a>
                    )}

                    {/* PDF Handling */}
                    {isPdf && (
                        <div className="flex flex-wrap gap-2 mt-2">
                            {/* Open Button */}
                            <a
                                href={fileUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-colors text-xs font-bold text-ash-gray hover:text-banana group/btn"
                            >
                                <DocumentTextIcon className="h-4 w-4 group-hover/btn:text-banana transition-colors" />
                                Open PDF
                            </a>

                            {/* Chat Button */}
                            <button
                                onClick={() => setIsChatOpen(true)}
                                className={`flex items-center gap-2 text-xs font-bold px-4 py-2 rounded-lg transition-all border border-transparent
                                    ${isProcessing
                                        ? 'bg-banana/5 text-banana animate-pulse cursor-wait'
                                        : 'text-banana hover:text-white bg-banana/10 hover:bg-banana/20 hover:border-banana/30'}`}
                            >
                                {isProcessing ? (
                                    <>
                                        <span className="animate-spin h-3 w-3 border-2 border-banana border-t-transparent rounded-full"></span>
                                        Reading file...
                                    </>
                                ) : (
                                    <>
                                        <ChatBubbleLeftRightIcon className="w-4 h-4" />
                                        Chat with PDF Agent
                                    </>
                                )}
                            </button>
                        </div>
                    )}

                    {/* Generic File Handling (if not image, pdf, or audio) */}
                    {!isImage && !isPdf && note.media_type !== 'voice' && !note.file_path?.endsWith('.wav') && (
                        <a href={fileUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 px-3 py-1.5 bg-white/5 rounded text-xs text-ash-gray hover:text-banana transition-colors mt-2">
                            <DocumentTextIcon className="h-3 w-3" />
                            Open Attachment
                        </a>
                    )}
                </div>
            )}

            {note.tags && note.tags.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                    {note.tags.map((tag, i) => (
                        <span key={`${tag}-${i}`} className="text-[10px] font-bold text-banana bg-banana/10 px-2 py-1 rounded hover:bg-banana/20 transition-colors cursor-pointer">#{tag}</span>
                    ))}
                </div>
            )}

            <AgentChatModal
                isOpen={isChatOpen}
                onClose={() => setIsChatOpen(false)}
                noteId={note.id}
                title={note.file_path ? note.file_path.split('/').pop() || 'PDF' : 'PDF Document'}
            />
        </div>
    );
};
