import { useState } from 'react';
import { SparklesIcon, ArrowDownTrayIcon, PlusIcon, CheckIcon } from '@heroicons/react/24/outline';
import axios from 'axios';
import { useNoteStore } from '../stores/noteStore';

interface GenResult {
    image: string; // Base64
    generation_time: number;
    seed: number;
    device: string;
}

export const ImageGen = () => {
    const [prompt, setPrompt] = useState('');
    const [steps, setSteps] = useState(9);
    const [width, setWidth] = useState(512);
    const [height, setHeight] = useState(512);
    const [guidanceScale, setGuidanceScale] = useState(0.0);
    const [seed, setSeed] = useState<number | ''>('');
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<GenResult | null>(null);
    const [error, setError] = useState('');

    // Add to Timeline State
    const [isAdding, setIsAdding] = useState(false);
    const [added, setAdded] = useState(false);
    const { uploadFile, createNote } = useNoteStore();

    const PRESETS = [
        { label: "Square (1024x1024)", w: 1024, h: 1024 },
        { label: "Square Fast (512x512)", w: 512, h: 512 },
        { label: "Landscape (1280x720)", w: 1280, h: 720 },
        { label: "Landscape Wide (1344x768)", w: 1344, h: 768 },
        { label: "Portrait (720x1280)", w: 720, h: 1280 },
        { label: "Portrait Tall (768x1344)", w: 768, h: 1344 },
    ];

    const handleGenerate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!prompt.trim()) return;

        setIsLoading(true);
        setError('');
        setResult(null);
        setAdded(false); // Reset added state on new generation

        try {
            const payload = {
                prompt,
                steps,
                seed: seed === '' ? null : Number(seed),
                width,
                height,
                guidance_scale: guidanceScale
            };

            const response = await axios.post('http://localhost:8000/api/image/generate', payload);
            setResult(response.data);
        } catch (err: any) {
            console.error("Generation failed", err);
            setError(err.response?.data?.detail || "Image generation failed. Ensure the backend is running and model is loaded.");
        } finally {
            setIsLoading(false);
        }
    };

    const downloadImage = () => {
        if (!result) return;
        const link = document.createElement('a');
        link.href = `data:image/png;base64,${result.image}`;
        link.download = `z-image-${result.seed}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const addToTimeline = async () => {
        if (!result || isAdding || added) return;

        setIsAdding(true);
        try {
            // Convert Base64 to Blob/File
            const byteString = atob(result.image);
            const ab = new ArrayBuffer(byteString.length);
            const ia = new Uint8Array(ab);
            for (let i = 0; i < byteString.length; i++) {
                ia[i] = byteString.charCodeAt(i);
            }
            const blob = new Blob([ab], { type: 'image/png' });
            const file = new File([blob], `z-image-${result.seed}.png`, { type: 'image/png' });

            // Upload via store actions (consistent with logic in NoteInput)
            const { filePath } = await uploadFile(file);

            // Create Note
            await createNote(
                prompt,
                'image',
                ['generated', 'z-image'],
                filePath
            );

            setAdded(true);
        } catch (err) {
            console.error("Failed to add to timeline", err);
            alert("Failed to save image to timeline.");
        } finally {
            setIsAdding(false);
        }
    };

    const handlePresetChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const [w, h] = e.target.value.split('x').map(Number);
        setWidth(w);
        setHeight(h);
    };

    return (
        <div className="max-w-2xl mx-auto space-y-8 animate-in fade-in duration-500">
            {/* Input Section */}
            <div className="bg-graphite p-6 rounded-3xl shadow-lg border border-white/5 relative group focus-within:ring-2 focus-within:ring-banana/50 transition-all">
                <form onSubmit={handleGenerate} className="space-y-6">
                    <div>
                        <label className="block text-xs font-bold text-ash-gray uppercase tracking-wider mb-2">Prompt</label>
                        <textarea
                            className="w-full p-4 bg-black/20 text-white placeholder-ash-gray/60 border border-white/10 focus:border-banana/50 focus:ring-0 resize-none rounded-xl text-lg min-h-[120px]"
                            placeholder="A futuristic cyberpunk city with neon lights..."
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            disabled={isLoading}
                        />
                    </div>

                    <div className="flex flex-col sm:flex-row gap-6">
                        <div className="flex-1">
                            <label className="flex justify-between text-xs font-bold text-ash-gray uppercase tracking-wider mb-2">
                                <span>Steps</span>
                                <span className="text-banana">{steps}</span>
                            </label>
                            <input
                                type="range"
                                min="1"
                                max="20"
                                value={steps}
                                onChange={(e) => setSteps(Number(e.target.value))}
                                className="w-full h-2 bg-black/40 rounded-lg appearance-none cursor-pointer accent-banana"
                                disabled={isLoading}
                            />
                            <p className="text-[10px] text-ash-gray mt-1">Lower = Faster, Higher = Detail (Default: 9)</p>
                        </div>
                        <div className="w-full sm:w-32">
                            <label className="block text-xs font-bold text-ash-gray uppercase tracking-wider mb-2">Resolution</label>
                            <select
                                value={`${width}x${height}`}
                                onChange={handlePresetChange}
                                className="w-full p-2 bg-black/20 text-white border border-white/10 rounded-lg text-sm focus:border-banana/50 focus:ring-0 appearance-none"
                                disabled={isLoading}
                            >
                                {PRESETS.map((p) => (
                                    <option key={p.label} value={`${p.w}x${p.h}`}>
                                        {p.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-6">
                        <div className="flex-1">
                            <label className="flex justify-between text-xs font-bold text-ash-gray uppercase tracking-wider mb-2">
                                <span>Guidance Scale</span>
                                <span className="text-banana">{guidanceScale.toFixed(1)}</span>
                            </label>
                            <input
                                type="range"
                                min="0"
                                max="10"
                                step="0.5"
                                value={guidanceScale}
                                onChange={(e) => setGuidanceScale(Number(e.target.value))}
                                className="w-full h-2 bg-black/40 rounded-lg appearance-none cursor-pointer accent-banana"
                                disabled={isLoading}
                            />
                        </div>
                        <div className="w-full sm:w-32">
                            <label className="block text-xs font-bold text-ash-gray uppercase tracking-wider mb-2">Seed</label>
                            <input
                                type="number"
                                placeholder="Random"
                                value={seed}
                                onChange={(e) => setSeed(e.target.value === '' ? '' : Number(e.target.value))}
                                className="w-full p-2 bg-black/20 text-white border border-white/10 rounded-lg text-sm focus:border-banana/50 focus:ring-0"
                                disabled={isLoading}
                            />
                        </div>
                    </div>

                    <div className="pt-2 flex justify-end">
                        <button
                            type="submit"
                            disabled={isLoading || !prompt.trim()}
                            className="bg-banana hover:bg-yellow-400 text-black px-8 py-3 rounded-full font-bold shadow-lg shadow-banana/10 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-transform active:scale-95 text-sm"
                        >
                            {isLoading ? (
                                <>
                                    <span className="animate-pulse">Dreaming...</span>
                                    <SparklesIcon className="h-5 w-5 animate-spin" />
                                </>
                            ) : (
                                <>
                                    <span>Generate</span>
                                    <SparklesIcon className="h-5 w-5" />
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>

            {/* Error Message */}
            {error && (
                <div className="bg-red-500/10 text-red-400 p-4 rounded-2xl text-center text-sm border border-red-500/20">
                    {error}
                </div>
            )}

            {/* Results Section */}
            {result && (
                <div className="bg-graphite p-2 rounded-3xl shadow-2xl border border-white/5 overflow-hidden animate-in zoom-in-95 duration-500">
                    <div className="relative group">
                        <img
                            src={`data:image/png;base64,${result.image}`}
                            alt="Generated"
                            className="w-full h-auto rounded-2xl object-cover"
                            style={{ aspectRatio: result.image ? `${width}/${height}` : 'auto' }}
                        />
                        <div className="absolute inset-x-0 bottom-0 p-4 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex justify-between items-end rounded-b-2xl">
                            <div className="text-xs text-white/80 font-mono">
                                <p>Time: <span className="text-banana">{result.generation_time}s</span></p>
                                <p>Seed: {result.seed}</p>
                                <p>Device: {result.device}</p>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={addToTimeline}
                                    disabled={isAdding || added}
                                    className={`p-2 rounded-full backdrop-blur-md transition-all flex items-center gap-2 px-4
                                        ${added
                                            ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                                            : 'bg-white/10 hover:bg-white/20 text-white'}`}
                                    title="Add to Timeline"
                                >
                                    {isAdding ? (
                                        <ArrowDownTrayIcon className="h-5 w-5 animate-spin" />
                                    ) : added ? (
                                        <>
                                            <CheckIcon className="h-5 w-5" />
                                            <span className="text-xs font-bold">Added</span>
                                        </>
                                    ) : (
                                        <>
                                            <PlusIcon className="h-5 w-5" />
                                            <span className="text-xs font-bold">Timeline</span>
                                        </>
                                    )}
                                </button>
                                <button
                                    onClick={downloadImage}
                                    className="bg-white/10 hover:bg-white/20 text-white p-2 rounded-full backdrop-blur-md transition-colors"
                                    title="Download"
                                >
                                    <ArrowDownTrayIcon className="h-5 w-5" />
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
