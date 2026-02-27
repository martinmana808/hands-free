import { create } from 'zustand';

interface AppState {
  transcript: string;
  isProcessing: boolean;
  style: string;
  setTranscript: (text: string) => void;
  appendTranscript: (text: string) => void;
  setIsProcessing: (status: boolean) => void;
  setStyle: (style: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  transcript: '',
  isProcessing: false,
  style: 'professional',
  setTranscript: (text) => set({ transcript: text }),
  appendTranscript: (text) => set((state) => ({ transcript: state.transcript + ' ' + text })),
  setIsProcessing: (status) => set({ isProcessing: status }),
  setStyle: (newStyle) => set({ style: newStyle }),
}));
