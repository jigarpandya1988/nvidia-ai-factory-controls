import React from 'react';

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export function DetailModal({ open, onClose, title, children }: Props) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      
      {/* Modal */}
      <div className="relative bg-surface-2 border border-surface-4 rounded-xl shadow-2xl w-[90%] max-w-2xl max-h-[85vh] overflow-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-surface-4 sticky top-0 bg-surface-2 z-10">
          <h2 className="text-sm font-semibold text-nvidia">{title}</h2>
          <button 
            onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded bg-surface-3 hover:bg-red-500/20 hover:text-red-400 transition-colors text-gray-400"
          >
            ✕
          </button>
        </div>
        {/* Body */}
        <div className="p-5">
          {children}
        </div>
      </div>
    </div>
  );
}
