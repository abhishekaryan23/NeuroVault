import { useNoteStore } from '../stores/noteStore';
import { NoteCard } from './NoteCard';
import { XMarkIcon, SparklesIcon } from '@heroicons/react/24/outline';

export const VoiceSearchModal = () => {
    const { searchResults, isVoiceSearch, setSearchQuery, isLoading } = useNoteStore();

    if (!isVoiceSearch) return null;

    const handleClose = () => {
        setSearchQuery('', false);
    };

    const hasResults = searchResults && searchResults.length > 0;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300">
            <div className="bg-graphite/90 backdrop-blur-xl border border-white/10 rounded-3xl shadow-2xl max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col relative animate-in zoom-in-95 duration-300">

                {/* Header */}
                <div className="p-6 border-b border-white/5 flex justify-between items-center bg-white/5">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-banana/20 rounded-full">
                            <SparklesIcon className="w-6 h-6 text-banana" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Voice Search Results</h2>
                            {isLoading ? (
                                <p className="text-sm text-ash-gray animate-pulse">Searching memories...</p>
                            ) : (
                                <p className="text-sm text-ash-gray">Found {searchResults.length} matching memories</p>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={handleClose}
                        className="p-2 hover:bg-white/10 rounded-full transition-colors text-ash-gray hover:text-white"
                    >
                        <XMarkIcon className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto custom-scrollbar bg-neural-pattern bg-cover bg-center min-h-[200px]">
                    {isLoading ? (
                        <div className="flex flex-col items-center justify-center h-full py-10 opacity-50">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-banana mb-2" />
                            <p className="text-sm text-banana">Scanning...</p>
                        </div>
                    ) : !hasResults ? (
                        <div className="flex flex-col items-center justify-center h-full py-10 text-ash-gray">
                            <p>No results found for your query.</p>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {searchResults.slice(0, 2).map((result) => (
                                <div key={result.note.id} className="transform hover:scale-[1.02] transition-transform duration-300">
                                    <NoteCard note={result.note} />
                                    <div className="mt-2 text-right">
                                        <span className="text-xs font-mono text-banana bg-banana/10 px-2 py-1 rounded-full">
                                            Match: {Math.round((1 - result.distance) * 100)}%
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer hint */}
                <div className="p-4 bg-black/20 text-center text-xs text-white/30 italic">
                    "Say 'Close' or click X to return."
                </div>
            </div>
        </div>
    );
};
