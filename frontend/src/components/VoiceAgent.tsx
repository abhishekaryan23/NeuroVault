import { useState, useRef } from 'react';
import { Mic, MicOff, Volume2, X, Loader2 } from 'lucide-react';
import { useNoteStore } from '../stores/noteStore';

// Utility to convert AudioBuffer to WAV Class-compliant Blob
const audioBufferToWav = (buffer: AudioBuffer): Blob => {
    const numChannels = 1; // Mono
    const sampleRate = buffer.sampleRate; // Use context rate (usually 44.1 or 48k)
    // Vosk expects 16k usually but robust model might handle others. 
    // Ideally we resample to 16k.
    // For simplicity, we send raw recorded rate and let Vosk/Soundfile handle it if possible.
    // But Vosk small model is strictly 16k often. 
    // Use offline resampling if needed.
    // Actually, simplest is to let Backend (Soundfile/Vosk) fail if mismatch? 
    // No, let's try to resample or at least just send valid WAV.

    // NOTE: Simple WAV encoding function
    const length = buffer.length * numChannels * 2 + 44;
    const out = new DataView(new ArrayBuffer(length));

    const writeString = (view: DataView, offset: number, string: string) => {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
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
    out.setUint16(20, 1, true); // PCM
    out.setUint16(22, numChannels, true);
    out.setUint32(24, sampleRate, true);
    out.setUint32(28, sampleRate * 2, true);
    out.setUint16(32, 2, true); // Align
    out.setUint16(34, 16, true); // 16 bit
    writeString(out, 36, 'data');
    out.setUint32(40, buffer.length * 2, true);

    // Interleave channels (if stereo) or just copy (mono)
    // We assume mono input from getUserMedia constraint
    floatTo16BitPCM(out, 44, buffer.getChannelData(0));

    return new Blob([out], { type: 'audio/wav' });
};


const VoiceAgent = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [isListening, setIsListening] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [response, setResponse] = useState('');
    const [transcript, setTranscript] = useState(''); // Holds status mostly now ("Recording...")

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const audioContextRef = useRef<AudioContext | null>(null);
    const streamRef = useRef<MediaStream | null>(null);

    // Start Recording
    const startRecording = async () => {
        try {
            setResponse('');
            setTranscript("Listening...");

            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;

            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                // Blob from MediaRecorder is usually webm/opus.
                // We need to convert to WAV for VoskBackend? 
                // Or we can use AudioContext to capture and encode.
                // MediaRecorder is easier but WebM.
                // Simple hack: Decode the WebM blob using AudioContext, then Re-encode as WAV.

                const webmBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                await processAudioForBackend(webmBlob);
            };

            mediaRecorder.start();
            setIsListening(true);

        } catch (err) {
            console.error("Mic Error:", err);
            setResponse("Microphone access denied or error.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isListening) {
            mediaRecorderRef.current.stop();
            setIsListening(false);
            // Stop tracks
            streamRef.current?.getTracks().forEach(track => track.stop());
        }
    };

    const processAudioForBackend = async (blob: Blob) => {
        setIsProcessing(true);
        setTranscript("Processing audio...");

        try {
            // 1. Decode WebM to AudioBuffer
            if (!audioContextRef.current) {
                audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
            }
            const arrayBuffer = await blob.arrayBuffer();
            const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer);

            // 2. Resample to 16kHz Mono (Vosk Requirement)
            const offlineCtx = new OfflineAudioContext(1, audioBuffer.duration * 16000, 16000);
            const source = offlineCtx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(offlineCtx.destination);
            source.start();
            const renderedBuffer = await offlineCtx.startRendering();

            // 3. Encode to WAV
            const wavBlob = audioBufferToWav(renderedBuffer);

            // 4. Send to Backend
            const formData = new FormData();
            formData.append("file", wavBlob, "recording.wav");

            const res = await fetch('http://localhost:8000/api/voice/command', {
                method: 'POST',
                body: formData
            });

            const data = await res.json();
            if (data.response) {
                setResponse(data.response);
                setTranscript("");

                // Refresh Stores to show new tasks/notes immediately
                const store = useNoteStore.getState();

                if (data.intent === 'SEARCH') {
                    console.log("[VoiceAgent] Handling SEARCH intent");

                    if (data.search_results && data.search_results.length > 0) {
                        console.log("[VoiceAgent] Using backend provided search results:", data.search_results.length);
                        store.setSearchQuery(data.query || "", true);
                        store.setSearchResults(data.search_results);
                    } else if (data.query) {
                        // Fallback to client-side search if no results provided but query exists
                        console.log("[VoiceAgent] Triggering client-side search for:", data.query);
                        store.setSearchQuery(data.query, true);
                        store.searchNotes(data.query);
                    }
                } else {
                    // For non-search, just refresh timeline/tasks
                    store.fetchTasks();
                    store.fetchTimeline();
                }

                if (data.audio) {
                    playAudio(data.audio);
                } else {
                    // Fallback to browser TTS if no audio returned (unlikely with our logic but safe)
                    speak(data.response);
                }
            } else {
                setTranscript("No response.");
            }

        } catch (e) {
            console.error("Audio Processing Error", e);
            setResponse("Error processing audio.");
        } finally {
            setIsProcessing(false);
        }
    };

    const playAudio = (base64String: string) => {
        try {
            const audio = new Audio(`data:audio/wav;base64,${base64String}`);
            audio.play();
        } catch (e) {
            console.error("Audio Playback Error", e);
        }
    };

    const speak = (text: string) => {
        // Fallback only
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.speak(utterance);
        }
    };

    const toggleListening = () => {
        if (isListening) {
            stopRecording();
        } else {
            startRecording();
        }
    };

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="fixed bottom-6 right-6 p-4 bg-purple-600 hover:bg-purple-500 text-white rounded-full shadow-xl transition-all z-50 group border border-white/20 focus:outline-none focus:ring-4 focus:ring-purple-500/50"
                aria-label="Open Voice Agent"
            >
                <Mic className="w-6 h-6 group-hover:scale-110 transition-transform" />
            </button>
        );
    }

    return (
        <div className="fixed bottom-6 right-6 w-80 bg-gray-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-4 flex flex-col gap-4 z-50 animate-in slide-in-from-bottom-10 fade-in duration-300">

            {/* Header */}
            <div className="flex justify-between items-center border-b border-white/5 pb-2">
                <h3 className="text-white font-medium flex items-center gap-2">
                    <Volume2 className="w-4 h-4 text-purple-400" />
                    Voice Agent (Local)
                </h3>
                <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-white transition-colors">
                    <X className="w-4 h-4" />
                </button>
            </div>

            {/* Content */}
            <div className="min-h-[100px] max-h-[300px] overflow-y-auto space-y-3 custom-scrollbar">
                {/* Status / Transcript */}
                {transcript && (
                    <div className="flex justify-end">
                        <div className="bg-purple-600/30 text-purple-100 px-3 py-2 rounded-2xl rounded-tr-sm text-sm max-w-[85%] border border-purple-500/30">
                            {transcript}
                        </div>
                    </div>
                )}

                {/* Agent Response */}
                {response && (
                    <div className="flex justify-start">
                        <div className="bg-gray-800/80 text-gray-200 px-3 py-2 rounded-2xl rounded-tl-sm text-sm max-w-[90%] border border-white/5">
                            {response}
                        </div>
                    </div>
                )}

                {/* Loading State */}
                {isProcessing && (
                    <div className="flex justify-start">
                        <div className="flex items-center gap-2 text-gray-400 text-xs px-2">
                            <Loader2 className="w-3 h-3 animate-spin" /> Processsing audio (Resampling & STT)...
                        </div>
                    </div>
                )}
            </div>

            {/* Controls */}
            <div className="flex justify-center pt-2">
                <button
                    onClick={toggleListening}
                    className={`
            p-6 rounded-full transition-all duration-300 flex items-center justify-center
            ${isListening
                            ? 'bg-red-500/20 text-red-400 ring-2 ring-red-500/50 scale-110 animate-pulse'
                            : 'bg-purple-600 hover:bg-purple-500 text-white shadow-lg hovering-scale'
                        }
          `}
                >
                    {isListening ? <MicOff className="w-8 h-8" /> : <Mic className="w-8 h-8" />}
                </button>
            </div>

            {isListening && (
                <div className="text-center text-xs text-gray-500 animate-pulse">
                    Recording...
                </div>
            )}
        </div>
    );
};

export default VoiceAgent;
