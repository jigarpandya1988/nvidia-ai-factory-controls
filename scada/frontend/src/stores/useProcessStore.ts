import { create } from 'zustand';
import { ProcessData } from '../types';

interface ProcessStore {
  current: ProcessData | null;
  history: ProcessData[];
  connected: boolean;
  setCurrent: (data: ProcessData) => void;
  setConnected: (connected: boolean) => void;
}

export const useProcessStore = create<ProcessStore>((set, get) => ({
  current: null,
  history: [],
  connected: false,
  setCurrent: (data) => {
    const history = [...get().history.slice(-300), data]; // Keep last 300 points (30s)
    set({ current: data, history });
  },
  setConnected: (connected) => set({ connected }),
}));
