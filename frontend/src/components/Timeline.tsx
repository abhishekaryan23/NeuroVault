import { useEffect } from 'react';
import { useNoteStore } from '../stores/noteStore';
import { NoteCard } from './NoteCard';
import { ClockIcon } from '@heroicons/react/24/outline'; // Need icon

export const Timeline = () => {
    const { notes, isLoading, fetchTimeline } = useNoteStore();

    useEffect(() => {
        fetchTimeline();
    }, [fetchTimeline]);

    if (isLoading && notes.length === 0) {
        return <div className="text-center py-20 text-ash-gray/50 animate-pulse">Loading timeline...</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-2 mb-6 border-b border-white/5 pb-2">
                <ClockIcon className="h-4 w-4 text-banana" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">Recent Activity</h2>
            </div>

            {notes.length === 0 ? (
                <div className="text-center py-20 bg-graphite/50 rounded-3xl border border-white/5 border-dashed">
                    <p className="text-ash-gray">No notes yet.</p>
                    <p className="text-sm text-ash-gray/50 mt-1">Start dumping your thoughts above!</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {notes.map((note) => (
                        <NoteCard key={note.id} note={note} />
                    ))}
                </div>
            )}
        </div>
    );
};
