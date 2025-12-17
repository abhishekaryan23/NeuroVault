import { useState, useRef } from 'react';
import { useNoteStore } from '../stores/noteStore';
import { PaperClipIcon, PaperAirplaneIcon } from '@heroicons/react/24/outline';
import axios from 'axios';

export const NoteInput = () => {
    const { createNote, fetchTimeline } = useNoteStore();
    const [content, setContent] = useState('');
    const [file, setFile] = useState<File | null>(null);

    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Optimistic Clear
        const pendingContent = content;
        const pendingFile = file;

        // Reset UI immediately
        setContent('');
        setFile(null);

        setIsUploading(false); // No blocking overlay needed anymore
        if (fileInputRef.current) fileInputRef.current.value = '';

        if (!pendingContent.trim() && !pendingFile) return;

        // If File, use Unified Upload Flow
        if (pendingFile) {
            try {
                const formData = new FormData();
                formData.append('file', pendingFile);
                if (pendingContent.trim()) {
                    formData.append('content', pendingContent);
                }

                // Fire and forget (mostly), UI updates via timeline polling
                await axios.post('http://localhost:8000/api/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });

                // Fetch to show "Processing..." card
                fetchTimeline();

            } catch (error) {
                console.error("Upload failed", error);
                alert("File upload failed. Please try again.");
                // Restore state? or leave it cleared? 
                // Currently leaving cleared, maybe user can retry from timeline?
                // But the note wasn't created if upload 500'd.
                // Restoring content would be nice, but for now simple behavior.
                setContent(pendingContent);
            }
        } else {
            // Text Only Flow (Legacy)
            await createNote(pendingContent, 'text', [], undefined);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="bg-graphite p-1.5 rounded-3xl shadow-lg border border-white/5 relative group focus-within:ring-2 focus-within:ring-banana/50 transition-all">


            <textarea
                className="w-full p-4 bg-transparent text-white placeholder-ash-gray border-none focus:ring-0 resize-none rounded-2xl text-base"
                rows={3}
                placeholder="What's on your mind?"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                disabled={isUploading}
            />

            <div className="flex justify-between items-center px-2 pb-2">
                <div className="flex items-center gap-2">
                    <label className={`cursor-pointer px-3 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-2 border border-transparent
                        ${file ? 'bg-banana/20 text-banana border-banana/20' : 'hover:bg-white/5 text-ash-gray hover:text-white'}`}>
                        <PaperClipIcon className="h-5 w-5" />
                        <span className="text-xs truncate max-w-[150px]">{file ? file.name : 'Attach (Img/Audio/PDF)'}</span>
                        <input
                            type="file"
                            className="hidden"
                            accept="image/*,audio/*,application/pdf"
                            ref={fileInputRef}
                            onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                        />
                    </label>
                    {file && (
                        <button
                            type="button"
                            onClick={() => {
                                setFile(null);
                                if (fileInputRef.current) fileInputRef.current.value = '';
                            }}
                            className="text-xs text-red-400 hover:text-red-300 transition-colors"
                        >
                            Remove
                        </button>
                    )}
                </div>

                <button
                    type="submit"
                    className="bg-banana hover:bg-yellow-400 text-black px-4 py-2 rounded-full font-bold shadow-lg shadow-banana/10 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 transition-transform active:scale-95"
                    disabled={isUploading || (!content && !file)}
                >
                    <span>{isUploading ? 'Uploading...' : 'Dump'}</span>
                    {!isUploading && <PaperAirplaneIcon className="h-4 w-4" />}
                </button>
            </div>
        </form>
    );
};
