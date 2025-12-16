import { useEffect, useState } from 'react';
import { useNoteStore } from '../stores/noteStore';
import { useSettingsStore } from '../stores/settingsStore';
import { CheckCircleIcon, ListBulletIcon, CalendarIcon, ChevronDownIcon, ChevronUpIcon, InformationCircleIcon } from '@heroicons/react/24/outline';
import { CheckCircleIcon as CheckCircleSolidIcon } from '@heroicons/react/24/solid';

export const TodoList = () => {
    const { tasks, fetchTasks, toggleTaskCompletion, isLoading } = useNoteStore();
    const { timezone } = useSettingsStore();
    const [isExpanded, setIsExpanded] = useState(false);
    const [expandedSourceId, setExpandedSourceId] = useState<number | null>(null);

    // Fetch source note details on demand could be done here, 
    // but for simplicity we rely on the backend potentially sending it 
    // OR we just assume we have enough info? 
    // Actually, 'tasks' list only contains the task notes. 
    // We need to fetch the ORIGIN note content if user requests it. 
    // Let's add a small local fetch logic or use store.
    const [sourceNotes, setSourceNotes] = useState<Record<number, any>>({});

    const fetchSource = async (originId: number) => {
        if (sourceNotes[originId]) return;
        try {
            const res = await fetch(`http://localhost:8000/api/notes/${originId}`);
            if (res.ok) {
                const data = await res.json();
                setSourceNotes(prev => ({ ...prev, [originId]: data }));
            }
        } catch (e) {
            console.error("Failed to fetch source", e);
        }
    };

    const toggleSource = (taskId: number, originId: number) => {
        if (expandedSourceId === taskId) {
            setExpandedSourceId(null);
        } else {
            setExpandedSourceId(taskId);
            fetchSource(originId);
        }
    };


    useEffect(() => {
        fetchTasks();
        // Poll every 30 seconds for updates
        const interval = setInterval(fetchTasks, 30000);
        return () => clearInterval(interval);
    }, [fetchTasks]);

    const handleToggle = (id: number, currentStatus: boolean | undefined) => {
        toggleTaskCompletion(id, !currentStatus);
    };

    // Derived State
    const events = tasks.filter(t => t.category === 'Event' && !t.is_completed);
    const activeTasks = tasks.filter(t => t.category !== 'Event' && !t.is_completed);
    const completedTasks = tasks.filter(t => t.is_completed);

    const totalActive = events.length + activeTasks.length;
    const shouldCollapse = totalActive > 5;
    const showCollapsed = shouldCollapse && !isExpanded;

    // Group Active Tasks
    const groupedTasks: Record<string, typeof tasks> = {};
    activeTasks.forEach(t => {
        const cat = (t.category || 'General');
        if (!groupedTasks[cat]) groupedTasks[cat] = [];
        groupedTasks[cat].push(t);
    });

    const taskOrder = ["Urgent", "Work", "Personal", "Home", "Finance", "Shopping", "Health", "General"];
    const taskCategories = Object.keys(groupedTasks).sort((a, b) => {
        const ia = taskOrder.indexOf(a);
        const ib = taskOrder.indexOf(b);
        if (ia !== -1 && ib !== -1) return ia - ib;
        if (ia !== -1) return -1;
        if (ib !== -1) return 1;
        return a.localeCompare(b);
    });

    return (
        <div
            className={`bg-graphite p-6 rounded-3xl border border-white/5 relative overflow-hidden shadow-2xl transition-all duration-500 ease-in-out flex flex-col ${showCollapsed ? 'max-h-[220px]' : 'min-h-[300px]'
                }`}
        >
            {/* Ambient Glow */}
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-neural-purple/20 rounded-full blur-3xl pointer-events-none"></div>

            <div className="flex justify-between items-center mb-6 relative z-10 flex-shrink-0">
                <button
                    onClick={() => shouldCollapse && setIsExpanded(!isExpanded)}
                    className={`flex items-center space-x-3 group ${shouldCollapse ? 'cursor-pointer' : 'cursor-default'}`}
                >
                    <div className="p-2 bg-neural-purple/10 rounded-full group-hover:bg-neural-purple/20 transition-colors">
                        <ListBulletIcon className="h-5 w-5 text-neural-purple" />
                    </div>
                    <div className="flex items-center gap-2">
                        <h2 className="text-xl font-bold text-white tracking-tight">Agenda</h2>
                        {shouldCollapse && (
                            <ChevronDownIcon
                                className={`h-4 w-4 text-ash-gray transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
                            />
                        )}
                    </div>
                </button>
                <span className="text-xs font-bold text-ash-gray uppercase tracking-wider bg-white/5 px-2 py-1 rounded">
                    {events.length + activeTasks.length} Active
                </span>
            </div>

            <div className={`relative z-10 flex-1 pr-2 custom-scrollbar space-y-6 ${showCollapsed ? 'overflow-hidden' : 'overflow-y-auto'}`}>

                {isLoading && tasks.length === 0 ? (
                    <div className="animate-pulse space-y-3">
                        <div className="h-12 bg-white/5 rounded-xl w-full"></div>
                        <div className="h-12 bg-white/5 rounded-xl w-full"></div>
                        <div className="h-12 bg-white/5 rounded-xl w-full"></div>
                    </div>
                ) : tasks.length === 0 ? (
                    <div className="text-center py-10 opacity-50">
                        <CheckCircleIcon className="h-12 w-12 mx-auto text-ash-gray mb-3" />
                        <p className="text-sm text-ash-gray">All caught up!</p>
                        <p className="text-xs text-ash-gray/60 mt-1">Say "Remind me to..." or "Meeting at..." to add items.</p>
                    </div>
                ) : (
                    <>
                        {/* 1. EVENTS SECTION */}
                        {events.length > 0 && (
                            <div className="space-y-2">
                                <h3 className="flex items-center gap-2 text-xs font-bold text-banana uppercase tracking-wider pl-1 mb-2">
                                    <CalendarIcon className="h-3 w-3" /> Events
                                </h3>
                                {events.map(event => (
                                    <div key={event.id} className="group flex items-start gap-3 p-3 rounded-xl bg-banana/5 border border-banana/10 hover:border-banana/30 transition-all">
                                        <button
                                            onClick={() => handleToggle(event.id, event.is_completed)}
                                            className="mt-1 flex-shrink-0 text-banana/50 hover:text-banana transition-colors"
                                        >
                                            <CheckCircleIcon className="h-5 w-5" />
                                        </button>
                                        <div className="flex-1">
                                            <div className="flex justify-between items-start">
                                                <p className="text-sm text-white font-medium leading-relaxed">
                                                    {event.content}
                                                </p>
                                                {event.origin_note_id && (
                                                    <button
                                                        onClick={() => toggleSource(event.id, event.origin_note_id!)}
                                                        className="text-banana/50 hover:text-banana ml-2 transition-colors"
                                                        title={expandedSourceId === event.id ? 'Hide Source Note' : 'View Source Note'}
                                                    >
                                                        <InformationCircleIcon className="h-4 w-4" />
                                                    </button>
                                                )}
                                            </div>
                                            <p className="text-[10px] text-banana/70 mt-1 font-mono flex items-center gap-1">
                                                <CalendarIcon className="h-3 w-3" />
                                                {event.event_at
                                                    ? new Date(event.event_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
                                                    : new Date(event.created_at).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
                                                }
                                            </p>

                                            {/* Expanded Source View */}
                                            {expandedSourceId === event.id && event.origin_note_id && (
                                                <div className="mt-2 p-2 bg-black/20 rounded-lg border border-white/5 text-xs text-ash-gray animate-in fade-in slide-in-from-top-1">
                                                    {sourceNotes[event.origin_note_id] ? (
                                                        <>
                                                            <div className="flex items-center gap-2 mb-1 opacity-70">
                                                                <span className="uppercase text-[8px] tracking-wider font-bold">Original Memory</span>
                                                                {sourceNotes[event.origin_note_id].media_type === 'voice' && <span className="bg-white/10 px-1 rounded text-[8px]">VOICE</span>}
                                                            </div>
                                                            <p className="italic">"{sourceNotes[event.origin_note_id].content}"</p>

                                                            {sourceNotes[event.origin_note_id].file_path && sourceNotes[event.origin_note_id].media_type === 'voice' && (
                                                                <audio
                                                                    controls
                                                                    className="w-full mt-2 h-6 opacity-80"
                                                                    src={`http://localhost:8000/files/audio/${sourceNotes[event.origin_note_id].file_path.split('/').pop()}`}
                                                                />
                                                            )}
                                                        </>
                                                    ) : (
                                                        <span className="animate-pulse">Loading source...</span>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* 2. TASKS SECTION */}
                        {activeTasks.length > 0 && (
                            <>
                                {events.length > 0 && <div className="h-px bg-white/5 my-4" />}
                                {taskCategories.map(cat => (
                                    <div key={cat} className="space-y-2 mb-4">
                                        <h3 className="text-xs font-bold text-neural-purple uppercase tracking-wider pl-1">{cat}</h3>
                                        {groupedTasks[cat].map(task => (
                                            <div
                                                key={task.id}
                                                className="group flex items-start gap-3 p-3 rounded-xl hover:bg-white/5 transition-colors border border-transparent hover:border-white/5 bg-white/5"
                                            >
                                                <button
                                                    onClick={() => handleToggle(task.id, task.is_completed)}
                                                    className="mt-1 flex-shrink-0 text-ash-gray hover:text-banana transition-colors"
                                                >
                                                    <CheckCircleIcon className="h-5 w-5" />
                                                </button>
                                                <div className="flex-1">
                                                    <p className="text-sm text-gray-200 leading-relaxed">
                                                        {task.content}
                                                    </p>
                                                    <p className="text-[10px] text-ash-gray mt-1 font-mono">
                                                        {new Date(task.created_at).toLocaleDateString()}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ))}
                            </>
                        )}

                        {/* 3. COMPLETED SECTION */}
                        {completedTasks.length > 0 && (
                            <div className="pt-4 border-t border-white/5 mt-6 opacity-60 hover:opacity-100 transition-opacity">
                                <h3 className="flex items-center gap-2 text-xs font-bold text-ash-gray uppercase tracking-wider pl-1 mb-3">
                                    <CheckCircleSolidIcon className="h-3 w-3" /> Completed
                                </h3>
                                <div className="space-y-2">
                                    {completedTasks.map(task => (
                                        <div key={task.id} className="flex items-center gap-3 p-2 pl-3 rounded-lg hover:bg-white/5 transition-colors group">
                                            <button
                                                onClick={() => handleToggle(task.id, true)}
                                                className="flex-shrink-0 text-green-500/50 hover:text-green-400 transition-colors"
                                            >
                                                <CheckCircleSolidIcon className="h-4 w-4" />
                                            </button>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs text-gray-400 line-through truncate">
                                                    {task.content}
                                                </p>
                                            </div>
                                            <div className="text-[10px] text-ash-gray/50 font-mono whitespace-nowrap flex items-center gap-1">
                                                {/* Use updated_at for completion time */}
                                                {new Date(task.updated_at || task.created_at).toLocaleTimeString('en-US', {
                                                    timeZone: timezone,
                                                    month: 'short',
                                                    day: 'numeric',
                                                    hour: '2-digit',
                                                    minute: '2-digit'
                                                })}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </>
                )}

                {shouldCollapse && isExpanded && (
                    <div className="pt-4 flex justify-center pb-2">
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                setIsExpanded(false);
                            }}
                            className="text-xs font-bold text-ash-gray hover:text-white uppercase tracking-wider flex items-center gap-1 bg-white/5 hover:bg-white/10 px-4 py-2 rounded-full transition-all border border-white/5 hover:border-white/20"
                        >
                            <ChevronUpIcon className="h-3 w-3" /> Minimize
                        </button>
                    </div>
                )}
            </div>

            {showCollapsed && (
                <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-graphite via-graphite/90 to-transparent flex items-end justify-center pb-4 z-20">
                    <button
                        onClick={() => setIsExpanded(true)}
                        className="text-xs font-bold text-banana hover:text-white uppercase tracking-wider flex items-center gap-1 bg-white/5 hover:bg-white/10 px-4 py-2 rounded-full transition-all border border-white/5 hover:border-banana/50"
                    >
                        View All ({totalActive} items) <ChevronDownIcon className="h-3 w-3" />
                    </button>
                </div>
            )}
        </div>
    );
};
