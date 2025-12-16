import { useState, useRef } from 'react';
import { useNoteStore } from '../stores/noteStore';
import { PaperClipIcon, PaperAirplaneIcon } from '@heroicons/react/24/outline';
import axios from 'axios';

export const NoteInput = () => {
    const { createNote, fetchTimeline } = useNoteStore();
    const [content, setContent] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!content.trim() && !file) return;

        let finalContent = content;
        let mediaType: any = 'text';
        let uploadedFilePath: string | undefined = undefined;
        let autoTags: string[] = [];

        // Upload Phase (Active)
        if (file) {
            setIsUploading(true);
            setUploadProgress(0);
            try {
                // Use axios for progress tracking
                const formData = new FormData();
                formData.append('file', file);

                const response = await axios.post('http://localhost:8000/api/upload', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                    onUploadProgress: (progressEvent) => {
                        const total = progressEvent.total || file.size;
                        const percent = Math.round((progressEvent.loaded * 100) / total);
                        setUploadProgress(percent);
                    }
                });

                const uploadResult = response.data;

                // PDF Logic: "Optimistic Transition"
                if (uploadResult.media_type === 'pdf') {
                    // Reset immediately (Passive Phase)
                    setContent('');
                    setFile(null);
                    setUploadProgress(0);
                    setIsUploading(false);
                    if (fileInputRef.current) fileInputRef.current.value = '';

                    // Refresh timeline to show the "Processing..." card
                    fetchTimeline();
                    return;
                }

                finalContent = content ? `${content}\n\n${uploadResult.extracted_content}` : uploadResult.extracted_content;
                mediaType = uploadResult.media_type;
                uploadedFilePath = uploadResult.file_path;
                autoTags = uploadResult.tags || [];

            } catch (error) {
                console.error("Upload failed", error);
                alert("File upload failed");
                setIsUploading(false);
                setUploadProgress(0);
                return;
            }
            setIsUploading(false);
        }

        await createNote(finalContent, mediaType, autoTags, uploadedFilePath);

        // Reset form
        setContent('');
        setFile(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    return (
        <form onSubmit={handleSubmit} className="bg-graphite p-1.5 rounded-3xl shadow-lg border border-white/5 relative group focus-within:ring-2 focus-within:ring-banana/50 transition-all">
            {isUploading && (
                <div className="absolute inset-0 bg-black/80 z-50 rounded-3xl flex flex-col items-center justify-center backdrop-blur-sm">
                    <div className="w-64 h-2 bg-white/20 rounded-full overflow-hidden mb-2">
                        <div
                            className="h-full bg-banana transition-all duration-200 ease-out"
                            style={{ width: `${uploadProgress}%` }}
                        />
                    </div>
                    <span className="text-banana font-bold text-sm">Uploading {uploadProgress}%</span>
                </div>
            )}

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
