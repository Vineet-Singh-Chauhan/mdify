import React, { useEffect, useRef, useState } from 'react';
import { Search } from 'lucide-react';
import { clsx } from 'clsx';

interface CommandItem {
  id: string;
  label: string;
  description: string;
  action: () => void;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  commands: CommandItem[];
}

export const CommandLinePalette: React.FC<Props> = ({ isOpen, onClose, commands }) => {
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = commands.filter(
    c =>
      c.label.toLowerCase().includes(query.toLowerCase()) ||
      c.description.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelected(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowDown') setSelected(s => Math.min(s + 1, filtered.length - 1));
      if (e.key === 'ArrowUp') setSelected(s => Math.max(s - 1, 0));
      if (e.key === 'Enter' && filtered[selected]) {
        filtered[selected].action();
        onClose();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, selected, filtered, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] bg-black/60 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div
        className="w-full max-w-lg bg-surface-800 border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10">
          <Search className="w-4 h-4 text-white/40 shrink-0" />
          <input
            ref={inputRef}
            id="command-palette-input"
            type="text"
            value={query}
            onChange={e => { setQuery(e.target.value); setSelected(0); }}
            placeholder="Type a command..."
            className="flex-1 bg-transparent text-white placeholder-white/30 outline-none text-sm"
          />
          <kbd className="text-white/20 text-xs border border-white/10 rounded px-1.5 py-0.5 font-mono">ESC</kbd>
        </div>
        <ul className="max-h-64 overflow-y-auto py-2" role="listbox">
          {filtered.length === 0 ? (
            <li className="px-4 py-8 text-center text-white/30 text-sm">No commands found</li>
          ) : (
            filtered.map((cmd, i) => (
              <li
                key={cmd.id}
                role="option"
                aria-selected={i === selected}
                onClick={() => { cmd.action(); onClose(); }}
                className={clsx(
                  'flex items-center justify-between px-4 py-3 cursor-pointer transition-colors duration-100',
                  i === selected ? 'bg-accent-500/20 text-white' : 'text-white/60 hover:text-white hover:bg-white/5',
                )}
              >
                <div>
                  <p className="text-sm font-medium">{cmd.label}</p>
                  <p className="text-xs text-white/30">{cmd.description}</p>
                </div>
                {i === selected && (
                  <kbd className="text-white/30 text-xs border border-white/10 rounded px-1.5 py-0.5 font-mono">⏎</kbd>
                )}
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
};
