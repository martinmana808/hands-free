import { useEffect, useRef } from 'react';
import { useAppStore } from './store';
import { useRecorder } from './hooks/useRecorder';
import { Mic, Square, Loader2, Sparkles } from 'lucide-react';

function App() {
  const { transcript, isProcessing, setTranscript, setIsProcessing } = useAppStore();
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.text) {
          setTranscript(message.text);
          setIsProcessing(false);
        }
      } catch (e) {
        console.error("Failed to parse ws message", e);
      }
    };

    return () => ws.close();
  }, [setTranscript, setIsProcessing]);

  const handleAudioData = (data: Blob) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
      if (!isProcessing) setIsProcessing(true);
    }
  };

  const { startRecording, stopRecording, isRecording } = useRecorder(handleAudioData);

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center py-12 px-4 selection:bg-indigo-500/30">
      
      {/* Header */}
      <header className="max-w-2xl w-full flex items-center justify-between mb-8">
        <div className="flex items-center gap-2">
          <div className="bg-indigo-500/20 p-2 rounded-xl">
            <Sparkles className="w-6 h-6 text-indigo-400" />
          </div>
          <h1 className="text-xl font-medium text-gray-100 tracking-tight">hands-free</h1>
        </div>
      </header>

      {/* Main Transcript Area */}
      <main className="max-w-2xl w-full flex-1 flex flex-col gap-6">
        <div className="flex-1 bg-gray-900/50 border border-gray-800/80 rounded-2xl p-6 min-h-[300px] relative overflow-hidden group">
          
          {transcript ? (
            <p className="text-lg text-gray-200 leading-relaxed whitespace-pre-wrap font-light">
              {transcript}
            </p>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-gray-600">
              <Mic className="w-12 h-12 mb-4 opacity-20" />
              <p>Hit record to start dictating...</p>
            </div>
          )}

          {isProcessing && (
            <div className="absolute bottom-4 left-6 flex items-center gap-2 text-indigo-400 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              Formatting...
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="flex justify-center mt-4">
          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`
              relative group flex items-center justify-center w-20 h-20 rounded-full transition-all duration-300 shadow-lg
              ${isRecording 
                ? 'bg-red-500/10 hover:bg-red-500/20 border-2 border-red-500/50 shadow-red-500/20' 
                : 'bg-indigo-500 hover:bg-indigo-600 hover:scale-105 shadow-indigo-500/25'}
            `}
          >
            {isRecording ? (
              <Square className="w-8 h-8 text-red-500 fill-red-500" />
            ) : (
              <Mic className="w-8 h-8 text-white" />
            )}

            {isRecording && (
              <span className="absolute -inset-4 rounded-full border border-red-500/30 animate-ping" />
            )}
          </button>
        </div>
      </main>

    </div>
  );
}

export default App;
