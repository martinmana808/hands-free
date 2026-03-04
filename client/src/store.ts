import { create } from 'zustand';

interface AppState {
  transcript: string;
  isProcessing: boolean;
  setTranscript: (text: string) => void;
  appendTranscript: (text: string) => void;
  setIsProcessing: (status: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  transcript: '',
  isProcessing: false,
  setTranscript: (text) => set({ transcript: text }),
  appendTranscript: (text) => set((state) => ({ transcript: state.transcript + ' ' + text })),
  setIsProcessing: (status) => set({ isProcessing: status }),
}));
