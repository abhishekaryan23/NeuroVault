import { useEffect } from 'react';
import { useNoteStore } from '../stores/noteStore';
import { useSettingsStore } from '../stores/settingsStore';
import { ArrowPathIcon, SparklesIcon } from '@heroicons/react/24/outline';

export const RollingSummary = () => {
    const { summary, isLoading, fetchSummary, refreshSummary } = useNoteStore();
    const { timezone } = useSettingsStore();

    useEffect(() => {
        fetchSummary();
    }, [fetchSummary]);

    if (!summary && !isLoading) {
        return (
            <div className="bg-gradient-to-br from-neural-purple/10 to-transparent p-8 rounded-3xl border border-neural-purple/20 text-center relative overflow-hidden group">
                <div className="absolute inset-0 bg-neural-purple/5 opacity-0 group-hover:opacity-100 transition-opacity blur-xl"></div>
                <div className="relative z-10">
                    <SparklesIcon className="h-10 w-10 text-neural-purple/70 mx-auto mb-3" />
                    <p className="text-white font-medium text-lg">No summary yet.</p>
                    <p className="text-sm text-ash-gray mt-1">Add some notes to kickstart your memory.</p>
                    <button
                        onClick={() => refreshSummary()}
                        className="mt-6 text-xs bg-neural-purple text-white px-5 py-2 rounded-full font-bold hover:bg-neural-purple/80 transition-all active:scale-95 shadow-lg shadow-neural-purple/20"
                    >
                        Generate Core Memory
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-graphite p-8 rounded-3xl border border-white/5 relative overflow-hidden shadow-2xl">
            {/* Ambient Glow */}
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-neural-purple/20 rounded-full blur-3xl pointer-events-none"></div>

            <div className="flex justify-between items-center mb-6 relative z-10">
                <div className="flex items-center space-x-3">
                    <div className="p-2 bg-neural-purple/10 rounded-full">
                        <SparklesIcon className="h-5 w-5 text-neural-purple" />
                    </div>
                    <h2 className="text-xl font-bold text-white tracking-tight">Rolling Summary</h2>
                </div>
                <button
                    onClick={() => refreshSummary()}
                    disabled={isLoading}
                    className="p-2 hover:bg-white/5 rounded-full transition-colors text-ash-gray hover:text-white"
                    title="Refresh Summary"
                >
                    <ArrowPathIcon className={`h-5 w-5 ${isLoading ? 'animate-spin text-banana' : ''}`} />
                </button>
            </div>

            <div className="prose prose-invert max-w-none text-gray-300 leading-relaxed relative z-10 font-light">
                {isLoading && !summary ? (
                    <div className="animate-pulse space-y-3">
                        <div className="h-4 bg-white/10 rounded w-3/4"></div>
                        <div className="h-4 bg-white/10 rounded w-1/2"></div>
                        <div className="h-4 bg-white/10 rounded w-5/6"></div>
                    </div>
                ) : (
                    (() => {
                        let content = summary?.summary_text;
                        let tasks: any[] = [];
                        try {
                            let cleanContent = content || "{}";
                            // Strip markdown code blocks
                            if (cleanContent.startsWith("```json")) cleanContent = cleanContent.slice(7);
                            if (cleanContent.startsWith("```")) cleanContent = cleanContent.slice(3);
                            if (cleanContent.endsWith("```")) cleanContent = cleanContent.slice(0, -3);

                            const parsed = JSON.parse(cleanContent.trim());
                            if (parsed.summary) {
                                content = parsed.summary;
                                tasks = parsed.tasks || [];
                            }
                        } catch (e) {
                            // legacy text
                        }

                        return (
                            <div className="space-y-4">
                                <p>{content}</p>
                                {tasks.length > 0 && (
                                    <div className="mt-6 overflow-hidden rounded-xl border border-white/5 bg-white/5">
                                        <table className="w-full text-left text-sm">
                                            <thead className="bg-black/20 text-xs uppercase text-ash-gray font-bold tracking-wider">
                                                <tr>
                                                    <th className="px-4 py-3">Task</th>
                                                    <th className="px-4 py-3 w-24">Priority</th>
                                                    <th className="px-4 py-3 w-32">Timeline</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-white/5">
                                                {tasks.map((task: any, idx: number) => (
                                                    <tr key={idx} className="hover:bg-white/5 transition-colors">
                                                        <td className="px-4 py-3 font-medium text-gray-200">{task.task}</td>
                                                        <td className="px-4 py-3">
                                                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase ${task.priority === 'High' ? 'bg-red-500/10 text-red-400' :
                                                                task.priority === 'Medium' ? 'bg-yellow-500/10 text-yellow-400' :
                                                                    'bg-blue-500/10 text-blue-400'
                                                                }`}>
                                                                {task.priority || 'Normal'}
                                                            </span>
                                                        </td>
                                                        <td className="px-4 py-3 text-xs text-ash-gray font-mono">
                                                            {task.timeline}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                            </div>
                        );
                    })()
                )}
            </div>

            {summary && (
                <div className="mt-6 pt-4 border-t border-white/5 flex justify-between items-center relative z-10">
                    <div className="text-[10px] text-ash-gray font-mono uppercase tracking-wider">
                        Context: {summary.date_bucket}
                    </div>
                    <div className="text-[10px] text-ash-gray font-mono">
                        Updated: {(() => {
                            const raw = summary.created_at;
                            const d = raw.endsWith('Z') || raw.includes('+') ? raw : `${raw}Z`;
                            return new Date(d).toLocaleTimeString('en-US', { timeZone: timezone, hour: '2-digit', minute: '2-digit' });
                        })()}
                    </div>
                </div>
            )}
        </div>
    );
};
