import React from 'react';
import { CheckCircle, Circle, Loader2, AlertCircle } from 'lucide-react';
import type { TaskState, PipelineStage } from '../types';
import { clsx } from 'clsx';

const STAGES: Array<{ key: PipelineStage; label: string }> = [
  { key: 'UPLOADED', label: 'File Uploaded & Validated' },
  { key: 'SCANNING', label: 'Sandbox Isolation & Malware Scan' },
  { key: 'PARSING', label: 'Parsing Text & Tables' },
  { key: 'RESOLVING_ASSETS', label: 'Resolving Image Assets' },
  { key: 'PACKAGING', label: 'Packaging Artifacts' },
];

const STAGE_ORDER = STAGES.map(s => s.key);

interface Props { state: TaskState; }

export const ProgressTimeline: React.FC<Props> = ({ state }) => {
  const currentIdx = STAGE_ORDER.indexOf(state.stage);

  return (
    <div className="flex flex-col gap-1 w-full" role="list" aria-label="Conversion progress">
      {STAGES.map(({ key, label }, idx) => {
        const isDone = idx < currentIdx || (idx === currentIdx && state.status === 'SUCCESS');
        const isActive = idx === currentIdx && state.status === 'ACTIVE';
        const isFailed = idx === currentIdx && state.status === 'FAILURE';
        const isPending = idx > currentIdx;

        return (
          <div
            key={key}
            role="listitem"
            className={clsx(
              'stage-indicator',
              isDone && 'text-success/90',
              isActive && 'text-accent-400 bg-accent-500/10',
              isFailed && 'text-danger',
              isPending && 'text-white/30',
            )}
          >
            {isDone && <CheckCircle className="w-5 h-5 shrink-0" />}
            {isActive && <Loader2 className="w-5 h-5 shrink-0 animate-spin" />}
            {isFailed && <AlertCircle className="w-5 h-5 shrink-0" />}
            {isPending && <Circle className="w-5 h-5 shrink-0" />}
            <span className="text-sm font-medium">{label}</span>
          </div>
        );
      })}
      {state.error_reason && (
        <p className="mt-2 text-danger text-sm px-4">{state.error_reason}</p>
      )}
    </div>
  );
};
