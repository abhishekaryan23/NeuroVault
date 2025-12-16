import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { XMarkIcon, SparklesIcon, ShieldCheckIcon, PaperAirplaneIcon, MicrophoneIcon, StopIcon } from '@heroicons/react/24/outline';

interface AgentChatModalProps {
    isOpen: boolean;
    onClose: () => void;
    noteId: number; // The Parent Note ID (PDF)
    title: string;
}

interface Message {
    role: 'user' | 'agent';
    content: string;
    verified?: boolean;
    correction?: string | null;
}

export const AgentChatModal: React.FC<AgentChatModalProps> = ({ isOpen, onClose, noteId, title }) => {
    const [query, setQuery] = useState('');
    const [messages, setMessages] = useState<Message[]>([]);
    const [status, setStatus] = useState<'idle' | 'thinking'>('idle');
    const [isListening, setIsListening] = useState(false);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [isPlayingAudio, setIsPlayingAudio] = useState(false);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const audioContextRef = useRef<AudioContext | null>(null);

    // Audio Helpers
    const audioBufferToWav = (buffer: AudioBuffer): Blob => {
        const numChannels = 1;
        const sampleRate = buffer.sampleRate;
        const length = buffer.length * numChannels * 2 + 44;
        const out = new DataView(new ArrayBuffer(length));
        const writeString = (view: DataView, offset: number, string: string) => {
            for (let i = 0; i < string.length; i++) view.setUint8(offset + i, string.charCodeAt(i));
        };
        const floatTo16BitPCM = (output: DataView, offset: number, input: Float32Array) => {
            for (let i = 0; i < input.length; i++, offset += 2) {
                let s = Math.max(-1, Math.min(1, input[i]));
                s = s < 0 ? s * 0x8000 : s * 0x7FFF;
                output.setInt16(offset, s, true);
            }
        };
        writeString(out, 0, 'RIFF');
        out.setUint32(4, 36 + buffer.length * 2, true);
        writeString(out, 8, 'WAVE');
        writeString(out, 12, 'fmt ');
        out.setUint32(16, 16, true);
        out.setUint16(20, 1, true);
        out.setUint16(22, numChannels, true);
        out.setUint32(24, sampleRate, true);
        out.setUint32(28, sampleRate * 2, true);
        out.setUint16(32, 2, true);
        out.setUint16(34, 16, true);
        writeString(out, 36, 'data');
        out.setUint32(40, buffer.length * 2, true);
        floatTo16BitPCM(out, 44, buffer.getChannelData(0));
        return new Blob([out], { type: 'audio/wav' });
    };

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) audioChunksRef.current.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const webmBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                await processAudio(webmBlob);
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            setIsListening(true);

        } catch (err) {
            console.error("Mic Error:", err);
            alert("Microphone access denied.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isListening) {
            mediaRecorderRef.current.stop();
            setIsListening(false);
        }
    };

    // Audio Queue System
    const audioQueueRef = useRef<string[]>([]);
    const isPlayingQueueRef = useRef(false);

    const playNextInQueue = async () => {
        console.log("[DEBUG] playNextInQueue. Queue size:", audioQueueRef.current.length);
        if (audioQueueRef.current.length === 0) {
            isPlayingQueueRef.current = false;
            setIsPlayingAudio(false);
            return;
        }

        isPlayingQueueRef.current = true;
        setIsPlayingAudio(true);

        const audioSrc = audioQueueRef.current.shift();
        if (!audioSrc) return;

        const audio = new Audio(audioSrc);
        audio.onended = () => {
            console.log("[DEBUG] Audio Ended. Next...");
            playNextInQueue();
        };
        audio.onerror = (e) => {
            console.error("[DEBUG] Audio Error Event:", e);
            playNextInQueue(); // Skip broken chunk
        }

        try {
            await audio.play();
            console.log("[DEBUG] Audio Playing...");
        } catch (e) {
            console.error("[DEBUG] Audio Play Exception:", e);
            // If autoplay blocked, this catches it
            playNextInQueue();
        }
    };

    const processAudio = async (blob: Blob) => {
        if (!isOpen) return;

        setIsTranscribing(true);
        try {
            if (!audioContextRef.current) {
                audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
            }
            const arrayBuffer = await blob.arrayBuffer();
            const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer);

            // Resample to 16kHz
            const offlineCtx = new OfflineAudioContext(1, audioBuffer.duration * 16000, 16000);
            const source = offlineCtx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(offlineCtx.destination);
            source.start();
            const renderedBuffer = await offlineCtx.startRendering();
            const wavBlob = audioBufferToWav(renderedBuffer);

            const formData = new FormData();
            formData.append("file", wavBlob, "recording.wav");

            // Use Streaming Endpoint
            const url = `http://localhost:8000/api/voice/pdf/${noteId}/stream`;

            const res = await fetch(url, { method: 'POST', body: formData });
            if (!res.body) throw new Error("No response body");

            const reader = res.body.getReader();
            const decoder = new TextDecoder();

            // Clear any old queue
            audioQueueRef.current = [];

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.query) {
                                setMessages(prev => [...prev, { role: 'user', content: data.query }]);
                                // Create placeholder for agent
                                setMessages(prev => [...prev, { role: 'agent', content: '', verified: false }]);
                            }

                            if (data.token) {
                                setMessages(prev => {
                                    const newMsgs = [...prev];
                                    const lastIndex = newMsgs.length - 1;
                                    // CRITICAL: Copy the object to avoid mutation in StrictMode (which causes double text)
                                    const lastMsg = { ...newMsgs[lastIndex] };

                                    if (lastMsg.role === 'agent') {
                                        lastMsg.content += data.token;
                                        newMsgs[lastIndex] = lastMsg;
                                    }
                                    return newMsgs;
                                });
                            }

                            if (data.audio) {
                                console.log("[DEBUG] Received Audio Chunk length:", data.audio.length);
                                const audioSrc = `data:audio/wav;base64,${data.audio}`;
                                audioQueueRef.current.push(audioSrc);

                                // Aggressively start if not flagged as playing
                                if (!isPlayingQueueRef.current) {
                                    console.log("[DEBUG] Starting Queue from idle state.");
                                    playNextInQueue();
                                } else {
                                    console.log("[DEBUG] Audio added to queue (Already playing).");
                                }
                            }

                            // Handle Verification Event
                            if (data.type === 'verification' || data.verified !== undefined) {
                                setMessages(prev => {
                                    const newMsgs = [...prev];
                                    const lastMsg = newMsgs[newMsgs.length - 1];
                                    if (lastMsg.role === 'agent') {
                                        lastMsg.verified = data.verified;
                                        lastMsg.correction = data.correction;
                                    }
                                    return newMsgs;
                                });
                            }

                        } catch (e) {
                            // ignore parse errors
                        }
                    }
                }
            }

            setIsTranscribing(false);

        } catch (e) {
            console.error("Audio Error", e);
            setIsTranscribing(false);
        }
    };

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Stop recording on close
    useEffect(() => {
        if (!isOpen) {
            stopRecording();
        }
    }, [isOpen]);

    const handleSend = async () => {
        if (!query.trim()) return;

        const userMsg = query;
        setQuery('');
        setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
        setStatus('thinking');

        // Create a placeholder for the agent's response
        setMessages(prev => [...prev, { role: 'agent', content: '', verified: false }]);

        try {
            // For text chat, we can keep using the stream endpoint or switch to non-stream.
            // Let's use the stream endpoint for text chat as it provides a nice typing effect.
            const response = await fetch(`http://localhost:8000/api/chat/pdf/${noteId}/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: userMsg })
            });

            if (!response.body) return;

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedText = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonStr = line.slice(6);
                        if (!jsonStr.trim()) continue;

                        try {
                            const data = JSON.parse(jsonStr);

                            if (data.token) {
                                accumulatedText += data.token;
                                setMessages(prev => {
                                    const newMsgs = [...prev];
                                    const lastMsg = newMsgs[newMsgs.length - 1];
                                    if (lastMsg.role === 'agent') {
                                        lastMsg.content = accumulatedText;
                                    }
                                    return newMsgs;
                                });
                            }
                        } catch (e) {
                            // ignore
                        }
                    }
                }
            }
            setStatus('idle');
        } catch (e) {
            setStatus('idle');
            setMessages(prev => [...prev, { role: 'agent', content: "Network error." }]);
        }
    };

    if (!isOpen) return null;

    return createPortal(
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
            <div className={`bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl w-full max-w-2xl h-[600px] flex flex-col border border-zinc-200 dark:border-zinc-800 transition-all`}>
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-zinc-200 dark:border-zinc-800">
                    <div className="flex items-center gap-2">
                        <div className={`p-2 rounded-lg bg-banana-100 text-banana-600`}>
                            <SparklesIcon className="w-5 h-5" />
                        </div>
                        <div>
                            <h3 className="font-semibold text-zinc-900 dark:text-zinc-100">
                                Chat with PDF
                            </h3>
                            <p className="text-xs text-zinc-500 truncate max-w-[300px]">
                                {isPlayingAudio ? 'Speaking...' : isListening ? 'Listening...' : title}
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full transition-colors">
                        <XMarkIcon className="w-5 h-5 text-zinc-500" />
                    </button>
                </div>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {messages.length === 0 && (
                        <div className="text-center mt-20 text-zinc-400">
                            <SparklesIcon className="w-12 h-12 mx-auto mb-3 opacity-20" />
                            <p>Ask me anything about this document.</p>
                            <p className="text-sm mt-2">I use <span className="font-bold text-banana-500">Gemma 3</span> to verify my answers.</p>
                        </div>
                    )}

                    {messages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[80%] rounded-2xl p-4 ${msg.role === 'user'
                                ? 'bg-banana-500 text-white rounded-tr-none'
                                : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200 rounded-tl-none'
                                }`}>
                                <p className="whitespace-pre-wrap text-sm">{msg.content}</p>

                                {msg.role === 'agent' && (
                                    <div className="mt-3 flex items-center gap-2 text-xs border-t border-black/5 pt-2">
                                        {msg.verified ? (
                                            <span className="flex items-center gap-1 text-green-600 font-medium">
                                                <ShieldCheckIcon className="w-3 h-3" /> Verified by Auditor
                                            </span>
                                        ) : (
                                            <span className="text-amber-600 font-medium">Unverified</span>
                                        )}
                                        {msg.correction && (
                                            <span className="text-zinc-400 italic ml-2">({msg.correction})</span>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {(status === 'thinking' || isTranscribing) && (
                        <div className="flex justify-start">
                            <div className="bg-zinc-100 dark:bg-zinc-800 rounded-2xl p-4 rounded-tl-none">
                                <div className="flex items-center gap-2 text-sm text-zinc-500">
                                    <span className="w-2 h-2 bg-banana-500 rounded-full animate-bounce" />
                                    <span className="w-2 h-2 bg-banana-500 rounded-full animate-bounce delay-100" />
                                    <span className="w-2 h-2 bg-banana-500 rounded-full animate-bounce delay-200" />
                                    {isTranscribing ? 'Processing audio...' : 'Thinking...'}
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div className="p-4 border-t border-zinc-200 dark:border-zinc-800">
                    <div className="flex items-center gap-2 bg-zinc-50 dark:bg-zinc-900/50 p-2 rounded-xl border border-zinc-200 dark:border-zinc-700 focus-within:ring-2 ring-banana-500/20 transition-all">
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                            placeholder="Ask a question..."
                            className="flex-1 bg-transparent border-none focus:ring-0 text-sm p-2 text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400"
                            disabled={status !== 'idle' || isListening}
                        />

                        {/* Standard Voice Input Button (Manual) */}
                        <button
                            onClick={isListening ? stopRecording : startRecording}
                            disabled={status !== 'idle' || isTranscribing}
                            className={`p-2 rounded-lg transition-colors ${isListening
                                ? 'bg-red-500 text-white animate-pulse'
                                : isTranscribing
                                    ? 'bg-zinc-200 text-zinc-400 cursor-wait'
                                    : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500 hover:text-banana-500 hover:bg-banana-50'
                                }`}
                            title={isListening ? "Stop Recording" : "Start Recording"}
                        >
                            {isListening ? (
                                <StopIcon className="w-5 h-5" />
                            ) : (
                                <MicrophoneIcon className="w-5 h-5" />
                            )}
                        </button>

                        <button
                            onClick={handleSend}
                            disabled={!query.trim() || status !== 'idle'}
                            className="p-2 bg-banana-500 text-white rounded-lg hover:bg-banana-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            <PaperAirplaneIcon className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </div>
        </div>,
        document.body
    );
};
