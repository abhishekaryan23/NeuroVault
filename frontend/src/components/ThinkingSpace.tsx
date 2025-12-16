import { useState, useEffect } from 'react';
import { useNoteStore } from '../stores/noteStore';
import { NoteCard } from './NoteCard';
import { MagnifyingGlassIcon, SparklesIcon, PhotoIcon } from '@heroicons/react/24/outline';

export const ThinkingSpace = () => {
    const { searchNotes, searchResults, searchQuery, setSearchQuery } = useNoteStore();
    // Local loading state to prevent flickering from other background fetches if needed, 
    // but better to rely on store or keep consistent. 
    // Actually, let's keep local isSearching for the specific search action feedback if needed,
    // or just rely on searchResults.length logic.
    const [isSearching, setIsSearching] = useState(false);
    const [selectedNote, setSelectedNote] = useState<any>(null);

    // Derived state
    const imageResults = searchResults.filter(r => r.note.media_type === 'image');

    // Initial Load: Fetch all images (empty query + media_type='image')
    useEffect(() => {
        const loadInitialImages = async () => {
            setIsSearching(true);
            await searchNotes('', 'image');
            setIsSearching(false);
        };
        // Only load if no query exists (persist state if navigating back?)
        // Or always refresh to ensure 'homepage' status.
        if (!searchQuery) {
            loadInitialImages();
        }
    }, []);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSearching(true);
        await searchNotes(searchQuery, 'image');
        setIsSearching(false);
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setSearchQuery(val);

        // Auto-reset to homepage if cleared
        if (val === '') {
            searchNotes('', 'image');
        }
    };

    return (
        <div className="h-full flex flex-col p-6 max-w-7xl mx-auto w-full relative">
            {/* Header */}
            <div className="text-center mb-8 space-y-2 z-10">
                <div className="inline-flex items-center justify-center p-3 bg-gradient-to-br from-banana/20 to-purple-500/20 rounded-2xl mb-2">
                    <SparklesIcon className="w-8 h-8 text-banana" />
                </div>
                <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white via-banana to-white">
                    Thinking Space
                </h1>
                <p className="text-ash-gray max-w-md mx-auto">
                    Explore your visual memories.
                </p>
            </div>

            {/* Search Bar */}
            <form onSubmit={handleSearch} className="mb-10 relative max-w-2xl mx-auto w-full group z-20">
                <div className="absolute inset-0 bg-gradient-to-r from-banana/20 to-purple-500/20 rounded-full blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                <div className="relative flex items-center bg-graphite/80 backdrop-blur-md border border-white/10 rounded-full px-6 py-4 shadow-2xl focus-within:ring-2 focus-within:ring-banana/50 transition-all">
                    <MagnifyingGlassIcon className="w-6 h-6 text-ash-gray mr-4" />
                    <input
                        type="text"
                        placeholder="Search your images..."
                        className="bg-transparent border-none focus:ring-0 text-white text-lg w-full placeholder-ash-gray/50"
                        value={searchQuery}
                        onChange={handleInputChange}
                    />
                    <button
                        type="submit"
                        disabled={isSearching}
                        className="ml-2 bg-banana text-black font-bold px-6 py-2 rounded-full hover:bg-yellow-400 transition-colors disabled:opacity-50"
                    >
                        {isSearching ? '...' : 'Search'}
                    </button>
                </div>
            </form>

            {/* Content Area: Loading or Grid */}
            {isSearching && searchResults.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center min-h-[300px] opacity-50">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-banana mb-4" />
                    <p className="text-banana animate-pulse">Finding memories...</p>
                </div>
            ) : (
                <>
                    {imageResults.length === 0 && !isSearching ? (
                        <div className="flex flex-col items-center justify-center text-center text-ash-gray col-span-full py-20 min-h-[300px] w-full items-center">
                            <PhotoIcon className="w-20 h-20 opacity-20 mb-4" />
                            <p className="text-lg">No images found.</p>
                            {searchQuery && <p className="text-sm opacity-60">Try a different search term.</p>}
                        </div>
                    ) : (
                        <div className="columns-2 md:columns-3 lg:columns-4 gap-4 space-y-4 pb-20">
                            {imageResults.map(result => {
                                // Robust URL construction
                                const rawPath = result.note.file_path || "";
                                const cleanPath = rawPath.replace("dumps/", "");
                                const imageUrl = `http://localhost:8000/files/${cleanPath}`;

                                return (
                                    <div key={result.note.id} className="break-inside-avoid group relative rounded-xl overflow-hidden cursor-pointer bg-gray-800 min-h-[100px]" onClick={() => setSelectedNote(result.note)}>
                                        <img
                                            src={imageUrl}
                                            alt={result.note.content || "memory"}
                                            className="w-full h-auto transform transition-transform duration-500 group-hover:scale-105"
                                            onError={(e) => {
                                                (e.target as HTMLImageElement).style.display = 'none';
                                                (e.target as HTMLImageElement).parentElement!.classList.add('flex', 'items-center', 'justify-center');
                                                (e.target as HTMLImageElement).parentElement!.innerHTML += '<span class="text-xs text-gray-500 p-2 break-all">Image Load Failed</span>';
                                            }}
                                        />
                                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors duration-300" />
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </>
            )}
            {/* Image Detail Modal */}
            {selectedNote && (
                <div className="fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/90 backdrop-blur-md" onClick={() => setSelectedNote(null)}>
                    <div className="max-w-2xl w-full relative" onClick={e => e.stopPropagation()}>
                        <button
                            onClick={() => setSelectedNote(null)}
                            className="absolute -top-12 right-0 text-white/50 hover:text-white transition-colors"
                        >
                            <span className="sr-only">Close</span>
                            ✕ Close
                        </button>
                        <NoteCard note={selectedNote} />
                    </div>
                </div>
            )}
        </div>
    );
};
