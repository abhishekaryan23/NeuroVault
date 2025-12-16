import { useState } from 'react';
import { Timeline } from './components/Timeline';
import { NoteInput } from './components/NoteInput';
import { TodoList } from './components/TodoList';
import { NoteCard } from './components/NoteCard';
import { ThinkingSpace } from './components/ThinkingSpace';
import { ImageGen } from './components/ImageGen';
import { Settings } from './components/Settings';
import CalendarView from './components/CalendarView';
import VoiceAgent from './components/VoiceAgent';
import { useNoteStore } from './stores/noteStore';
import { MagnifyingGlassIcon, XMarkIcon, Cog6ToothIcon, SparklesIcon, PhotoIcon, CalendarIcon } from '@heroicons/react/24/outline';

import { VoiceSearchModal } from './components/VoiceSearchModal';

function App() {
  const [view, setView] = useState<'timeline' | 'thinking' | 'image' | 'settings' | 'calendar'>('timeline');
  const { searchNotes, searchResults, searchQuery, setSearchQuery } = useNoteStore();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    searchNotes(searchQuery);
  };

  const clearSearch = () => {
    setSearchQuery('', false);
    searchNotes('');
  };

  return (
    <div className="min-h-screen bg-nano-dark text-white font-sans selection:bg-banana selection:text-black">
      {/* Voice Search Modal Popup */}
      <VoiceSearchModal />

      {/* Header */}
      <header className="sticky top-0 z-50 bg-nano-dark/80 backdrop-blur-md border-b border-white/5">
        <div className="max-w-3xl mx-auto px-6 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold tracking-tight text-white cursor-pointer hover:text-white/80 transition-opacity" onClick={() => setView('timeline')}>
            Neuro<span className="text-banana">Vault</span>
          </h1>

          <div className="flex items-center gap-4">
            <form onSubmit={handleSearch} className="relative w-64 group hidden sm:block">
              <input
                type="text"
                placeholder="Search memories..."
                className="w-full pl-10 pr-4 py-2 rounded-full bg-graphite border border-white/5 text-sm text-white placeholder-ash-gray focus:outline-none focus:ring-2 focus:ring-banana/50 transition-all group-hover:bg-[#252528]"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value, false)}
              />
              <MagnifyingGlassIcon className="h-4 w-4 text-ash-gray absolute left-3.5 top-1/2 transform -translate-y-1/2 group-focus-within:text-banana transition-colors" />
            </form>

            <button
              onClick={() => setView('settings')}
              className={`p-2 rounded-full transition-colors ${view === 'settings' ? 'bg-banana/10 text-banana' : 'text-ash-gray hover:text-white hover:bg-white/5'}`}
              title="Settings"
            >
              <Cog6ToothIcon className="h-6 w-6" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-10">

        {/* Navigation Tabs */}
        {view !== 'settings' && (
          <div className="flex justify-center space-x-6 border-b border-white/5 pb-4 mb-8">
            <button
              onClick={() => setView('timeline')}
              className={`text-sm font-bold pb-4 border-b-2 transition-all ${view === 'timeline' ? 'text-banana border-banana' : 'text-ash-gray border-transparent hover:text-white'}`}
            >
              Timeline
            </button>
            <button
              onClick={() => setView('thinking')}
              className={`text-sm font-bold pb-4 border-b-2 transition-all ${view === 'thinking' ? 'text-banana border-banana' : 'text-ash-gray border-transparent hover:text-white'}`}
            >
              Thinking Space
            </button>

            <button
              onClick={() => setView('image')}
              className={`text-sm font-bold pb-4 border-b-2 transition-all ${view === 'image' ? 'text-banana border-banana' : 'text-ash-gray border-transparent hover:text-white'} flex items-center gap-2`}
            >
              <PhotoIcon className="h-4 w-4" />
              Image Gen
            </button>
          </div>
        )}

        {view === 'settings' ? (
          <Settings />
        ) : view === 'image' ? (
          <ImageGen />
        ) : view === 'timeline' ? (
          <>
            {/* Todo List / Reminders Section */}
            <TodoList />

            {/* Note Input Area */}
            <NoteInput />

            {/* Search Results Override */}
            {searchQuery && searchResults.length > 0 ? (
              <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="flex justify-between items-center mb-6 border-b border-white/5 pb-2">
                  <div className="flex items-center gap-2">
                    <SparklesIcon className="h-4 w-4 text-banana" />
                    <h2 className="text-sm font-bold text-white uppercase tracking-wider">Search Results</h2>
                  </div>
                  <button
                    onClick={clearSearch}
                    className="text-xs flex items-center gap-1 text-ash-gray hover:text-white transition-colors"
                  >
                    <XMarkIcon className="h-3 w-3" /> Clear
                  </button>
                </div>
                <div className="space-y-4">
                  {searchResults.map((result, idx) => (
                    <div key={idx} className="relative group">
                      <div className="absolute -left-16 top-4 text-[10px] font-mono text-ash-gray opacity-0 group-hover:opacity-100 transition-opacity">
                        {(1 - result.distance).toFixed(2)}
                      </div>
                      <NoteCard note={result.note} />
                    </div>
                  ))}
                </div>
              </div>
            ) : searchQuery && searchResults.length === 0 ? (
              <div className="text-center py-20">
                <MagnifyingGlassIcon className="h-12 w-12 text-graphite mx-auto mb-4" />
                <p className="text-ash-gray">No memories found for "{searchQuery}".</p>
                <button onClick={clearSearch} className="mt-4 text-banana text-sm hover:underline">Clear search</button>
              </div>
            ) : (
              /* Default Timeline */
              <Timeline />
            )}
          </>
        ) : view === 'calendar' ? (
          <CalendarView />
        ) : (
          <ThinkingSpace />
        )}

        {/* VoiceAgent component */}
        <VoiceAgent />

        {/* Calendar FAB (Left Side, Purple Theme) */}
        <button
          onClick={() => setView(view === 'calendar' ? 'timeline' : 'calendar')}
          className={`fixed bottom-6 left-6 p-4 rounded-full shadow-xl transition-all z-50 group border border-white/20
            ${view === 'calendar' ? 'bg-purple-700 text-white ring-2 ring-purple-400' : 'bg-purple-600 hover:bg-purple-500 text-white'}`}
          title="Calendar"
        >
          <CalendarIcon className="w-6 h-6 group-hover:scale-110 transition-transform" />
        </button>
      </main>
    </div>
  );
}

export default App;
