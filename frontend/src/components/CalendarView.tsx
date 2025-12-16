import { useState, useMemo, useEffect } from 'react';
import {
    format,
    startOfMonth,
    endOfMonth,
    eachDayOfInterval,
    isSameDay,
    addMonths,
    subMonths,
    isToday,
    startOfWeek,
    endOfWeek,
    isSameMonth
} from 'date-fns';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/solid';
import { XMarkIcon, ClockIcon } from '@heroicons/react/24/outline';
import { useNoteStore } from '../stores/noteStore';

export default function CalendarView() {
    const [currentDate, setCurrentDate] = useState(new Date());
    const [selectedDate, setSelectedDate] = useState<Date | null>(null);

    const tasks = useNoteStore((state) => state.tasks);
    const fetchTasks = useNoteStore((state) => state.fetchTasks);

    useEffect(() => {
        fetchTasks();
    }, [fetchTasks]);

    // Filter for events
    const events = useMemo(() => {
        return tasks.filter(n => n.event_at);
    }, [tasks]);

    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(currentDate);
    const startDate = startOfWeek(monthStart);
    const endDate = endOfWeek(monthEnd);

    const calendarDays = eachDayOfInterval({ start: startDate, end: endDate });

    const nextMonth = () => setCurrentDate(addMonths(currentDate, 1));
    const prevMonth = () => setCurrentDate(subMonths(currentDate, 1));

    // Get events for the selected date
    const selectedEvents = useMemo(() => {
        if (!selectedDate) return [];
        return events.filter(e => e.event_at && isSameDay(new Date(e.event_at), selectedDate));
    }, [selectedDate, events]);

    return (
        <div className="flex flex-col h-full p-6 text-white overflow-hidden relative">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-yellow-300 to-yellow-500">
                    {format(currentDate, 'MMMM yyyy')}
                </h2>
                <div className="flex gap-2">
                    <button onClick={prevMonth} className="p-2 rounded-full hover:bg-white/10 transition">
                        <ChevronLeftIcon className="w-6 h-6" />
                    </button>
                    <button onClick={nextMonth} className="p-2 rounded-full hover:bg-white/10 transition">
                        <ChevronRightIcon className="w-6 h-6" />
                    </button>
                </div>
            </div>

            {/* Days Header */}
            <div className="grid grid-cols-7 gap-4 mb-2 opacity-70 font-semibold text-center">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                    <div key={day}>{day}</div>
                ))}
            </div>

            {/* Grid */}
            <div className="grid grid-cols-7 gap-4 flex-1 overflow-y-auto">
                {calendarDays.map(day => {
                    const dayEvents = events.filter(e => e.event_at && isSameDay(new Date(e.event_at), day));
                    const isTodayFlag = isToday(day);
                    const isCurrentMonth = isSameMonth(day, monthStart);

                    return (
                        <div
                            key={day.toISOString()}
                            onClick={() => setSelectedDate(day)}
                            className={`min-h-[100px] p-2 rounded-xl border backdrop-blur-md transition flex flex-col gap-1 cursor-pointer
                            ${!isCurrentMonth ? 'opacity-30 border-white/5 bg-black/10' : 'border-white/5 hover:border-banana/30 bg-black/20 hover:bg-black/40'}
                            ${isTodayFlag ? 'bg-white/10 ring-1 ring-yellow-400/50' : ''}
                        `}
                        >
                            <div className={`text-sm font-medium ${isTodayFlag ? 'text-yellow-400' : 'text-gray-400'}`}>
                                {format(day, 'd')}
                            </div>

                            {/* Events List (Preview) */}
                            <div className="flex flex-col gap-1 mt-1 overflow-y-auto max-h-[80px]">
                                {dayEvents.slice(0, 3).map(ev => (
                                    <div key={ev.id} className="text-[10px] p-1 rounded bg-yellow-500/20 border border-yellow-500/30 text-yellow-100 truncate">
                                        {ev.event_at && format(new Date(ev.event_at), 'HH:mm')} {ev.content}
                                    </div>
                                ))}
                                {dayEvents.length > 3 && (
                                    <div className="text-[10px] text-gray-400 pl-1">
                                        +{dayEvents.length - 3} more
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Event Modal Overlay */}
            {selectedDate && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200" onClick={() => setSelectedDate(null)}>
                    <div
                        className="bg-[#1c1c1e] w-full max-w-md rounded-2xl border border-white/10 shadow-2xl p-6 relative animate-in zoom-in-95 duration-200"
                        onClick={(e) => e.stopPropagation()} // Prevent close on content click
                    >
                        <button
                            onClick={() => setSelectedDate(null)}
                            className="absolute top-4 right-4 p-1 rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition"
                        >
                            <XMarkIcon className="w-6 h-6" />
                        </button>

                        <h3 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-yellow-300 to-yellow-500 mb-1">
                            {format(selectedDate, 'EEEE')}
                        </h3>
                        <p className="text-gray-400 mb-6 font-medium">
                            {format(selectedDate, 'MMMM do, yyyy')}
                        </p>

                        <div className="space-y-3 max-h-[60vh] overflow-y-auto px-1">
                            {selectedEvents.length > 0 ? (
                                selectedEvents.map((ev) => (
                                    <div key={ev.id} className="flex gap-4 p-4 rounded-xl bg-white/5 border border-white/5 hover:border-banana/30 transition group">
                                        <div className="flex flex-col items-center justify-center w-14 h-14 rounded-full bg-black/30 border border-white/10 shrink-0">
                                            <div className="text-xs text-banana font-bold">
                                                {ev.event_at && format(new Date(ev.event_at), 'HH:mm')}
                                            </div>
                                            <div className="text-[10px] text-gray-500">
                                                {ev.event_duration ? `${ev.event_duration}m` : '1h'}
                                            </div>
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h4 className="text-white font-medium truncate group-hover:text-banana transition-colors">
                                                {ev.content}
                                            </h4>
                                            <div className="flex items-center gap-2 mt-1">
                                                <span className="text-xs text-gray-400 flex items-center gap-1">
                                                    <ClockIcon className="w-3 h-3" />
                                                    {ev.event_at && (() => {
                                                        const start = new Date(ev.event_at);
                                                        const end = new Date(start.getTime() + (ev.event_duration || 60) * 60000);
                                                        return `${format(start, 'h:mm a')} - ${format(end, 'h:mm a')}`;
                                                    })()}
                                                </span>
                                                {ev.category && (
                                                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/10 text-gray-300">
                                                        {ev.category}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                                    <ClockIcon className="w-12 h-12 mb-3 opacity-20" />
                                    <p>No events scheduled</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
