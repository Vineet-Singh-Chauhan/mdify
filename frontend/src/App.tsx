import React, { useCallback, useEffect, useState } from 'react';
import { UploadDashboard } from './components/UploadDashboard';
import { BackgroundLayer } from './components/BackgroundLayer';
import { CommandLinePalette } from './components/CommandLinePalette';

const App: React.FC = () => {
  const [paletteOpen, setPaletteOpen] = useState(false);

  const handleKeydown = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      setPaletteOpen(prev => !prev);
    }
  }, []);

  useEffect(() => {
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  }, [handleKeydown]);

  const commands = [
    { id: 'convert', label: 'Convert a File', description: 'Upload and convert a document to Markdown', action: () => document.getElementById('drop-zone')?.click() },
    { id: 'reset', label: 'Clear Queue', description: 'Clear all queued files', action: () => document.getElementById('reset-btn')?.click() },
    { id: 'standalone', label: 'Set Standalone Mode', description: 'Output as a single .md file', action: () => document.getElementById('output-mode-standalone')?.click() },
    { id: 'package', label: 'Set ZIP Package Mode', description: 'Output as ZIP with images folder', action: () => document.getElementById('output-mode-package')?.click() },
  ];

  return (
    <div className="relative min-h-screen bg-surface-900 text-white overflow-hidden">
      <BackgroundLayer />
      <main className="relative z-10">
        <UploadDashboard />
      </main>
      <CommandLinePalette
        isOpen={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        commands={commands}
      />
      {/* Keyboard shortcut hint */}
      <div className="fixed bottom-4 right-4 text-white/20 text-xs font-mono flex items-center gap-1.5">
        <kbd className="border border-white/10 rounded px-1.5 py-0.5">⌘ K</kbd>
        <span>Command palette</span>
      </div>
    </div>
  );
};

export default App;
