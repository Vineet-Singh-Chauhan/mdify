import React, { useCallback, useRef, useState, useEffect } from 'react';
import { Upload, FileText, Package, Download, AlertTriangle } from 'lucide-react';
import { clsx } from 'clsx';
import { uploadFile, uploadBatch, getDownloadUrl, getBatchDownloadUrl, fetchStats, incrementVisitorCount } from '../api';
import { useConversionTask } from '../hooks/useConversionTask';
import { ProgressTimeline } from './ProgressTimeline';
import type { OutputMode } from '../types';

type FileEntry = { file: File; taskId: string | null; error: string | null };

export const UploadDashboard: React.FC = () => {
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [outputMode, setOutputMode] = useState<OutputMode>('standalone');
  const [isDragging, setIsDragging] = useState(false);
  const [primaryTaskId, setPrimaryTaskId] = useState<string | null>(null);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const [stats, setStats] = useState<{ visitors: number; conversions: number } | null>(null);
  const taskState = useConversionTask(batchId || primaryTaskId, !!batchId);

  useEffect(() => {
    const hasVisited = localStorage.getItem('mdify-visited');
    if (!hasVisited) {
      incrementVisitorCount()
        .then((res) => {
          setStats(res);
          localStorage.setItem('mdify-visited', 'true');
        })
        .catch(() => {
          fetchStats().then(setStats).catch(() => {});
        });
    } else {
      fetchStats().then(setStats).catch(() => {});
    }
  }, []);

  const addFiles = (incoming: File[]) => {
    const totalCount = files.length + incoming.length;
    if (totalCount > 10) {
      setGlobalError("You can only convert up to 10 files in a single batch.");
      const allowedCount = 10 - files.length;
      if (allowedCount > 0) {
        const allowedFiles = incoming.slice(0, allowedCount);
        setFiles(prev => [
          ...prev,
          ...allowedFiles.map(f => ({ file: f, taskId: null, error: null })),
        ]);
      }
    } else {
      setGlobalError(null);
      setFiles(prev => [
        ...prev,
        ...incoming.map(f => ({ file: f, taskId: null, error: null })),
      ]);
    }
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    addFiles(Array.from(e.dataTransfer.files));
  }, []);

  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const onDragLeave = () => setIsDragging(false);

  const handleConvert = async () => {
    if (files.length === 0) return;
    if (files.length > 10) {
      setGlobalError("You can only convert up to 10 files in a single batch.");
      return;
    }
    setIsUploading(true);
    setGlobalError(null);
    try {
      if (files.length === 1) {
        const res = await uploadFile(files[0].file, outputMode);
        setPrimaryTaskId(res.task_id);
        setFiles([{ file: files[0].file, taskId: res.task_id, error: null }]);
      } else {
        const res = await uploadBatch(files.map(f => f.file), outputMode);
        setBatchId(res.batch_id);
        setPrimaryTaskId(res.task_ids[0] ?? null);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Conversion failed. Please try again.';
      setGlobalError(message);
    } finally {
      setIsUploading(false);
    }
  };

  const handleReset = () => {
    setFiles([]);
    setPrimaryTaskId(null);
    setBatchId(null);
    setGlobalError(null);
  };

  const canDownload = taskState?.status === 'SUCCESS';

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6">
      {/* Header */}
      <div className="mb-10 text-center">
        <div className="inline-flex items-center gap-2 bg-accent-500/20 border border-accent-400/30 rounded-full px-4 py-1.5 text-accent-400 text-xs font-mono mb-4">
          <span className="w-1.5 h-1.5 bg-accent-400 rounded-full animate-pulse" />
          INSTANT PROCESSING — DATA IS DELETED SOON AFTER PROCESSING.
        </div>
        <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-br from-white via-white/90 to-accent-400 bg-clip-text text-transparent">
          mdify
        </h1>
        <p className="text-white/50 mt-3 text-lg font-light">
          Convert any document to clean Markdown
        </p>
        
      </div>

      {/* Main card */}
      <div className="w-full max-w-2xl glass rounded-2xl p-8 shadow-2xl shadow-black/40">
        {/* Output mode toggle */}
        <div className="flex gap-2 mb-6" role="group" aria-label="Output mode">
          {(['standalone', 'package'] as OutputMode[]).map(mode => (
            <button
              key={mode}
              id={`output-mode-${mode}`}
              onClick={() => setOutputMode(mode)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                outputMode === mode
                  ? 'bg-accent-500 text-white shadow-lg shadow-accent-500/30'
                  : 'text-white/50 hover:text-white border border-white/10 hover:border-white/20',
              )}
            >
              {mode === 'standalone' ? <FileText className="w-4 h-4" /> : <Package className="w-4 h-4" />}
              {mode === 'standalone' ? 'Standalone .md' : 'ZIP Package'}
            </button>
          ))}
        </div>

        {/* Drop zone */}
        {files.length === 0 ? (
          <div
            id="drop-zone"
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onClick={() => inputRef.current?.click()}
            role="button"
            tabIndex={0}
            aria-label="Drop zone for file upload"
            onKeyDown={e => e.key === 'Enter' && inputRef.current?.click()}
            className={clsx(
              'border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200',
              isDragging
                ? 'border-accent-400 bg-accent-500/10 scale-[1.01]'
                : 'border-white/20 hover:border-accent-400/50 hover:bg-white/5',
            )}
          >
            <Upload className="w-10 h-10 mx-auto mb-4 text-accent-400/70" />
            <p className="text-white/70 font-medium">
              Drop files here or{' '}
              <span className="text-accent-400 underline underline-offset-2">browse</span>
            </p>
            <p className="text-white/30 text-xs mt-2">
              PDF, DOCX, XLSX, HTML, TXT, CSV, JSON, XML • Max 50 MB per file
            </p>
            <input
              ref={inputRef}
              type="file"
              id="file-input"
              multiple
              accept=".pdf,.docx,.xlsx,.html,.htm,.txt,.csv,.json,.xml"
              className="hidden"
              onChange={e => addFiles(Array.from(e.target.files ?? []))}
            />
          </div>
        ) : (
          <div className="space-y-4">
            {batchId && (
              <div className="text-xs font-mono text-white/30 px-1">
                Batch ID: {batchId}
              </div>
            )}
            {/* File list */}
            <ul className="space-y-2" aria-label="Selected files">
              {files.map(({ file }, i) => (
                <li key={i} className="flex items-center gap-3 bg-surface-700/60 rounded-lg px-4 py-3">
                  <FileText className="w-4 h-4 text-accent-400 shrink-0" />
                  <span className="text-sm text-white/80 truncate flex-1">{file.name}</span>
                  <span className="text-xs text-white/30">{(file.size / 1024 / 1024).toFixed(1)} MB</span>
                </li>
              ))}
            </ul>

            {/* Progress */}
            {(primaryTaskId || batchId) && (
              <div className="bg-surface-700/40 rounded-xl p-4">
                <ProgressTimeline
                  state={taskState || {
                    task_id: (batchId || primaryTaskId)!,
                    batch_id: batchId,
                    original_name: files.length > 1 ? `${files.length} files` : files[0]?.file.name || 'document',
                    output_mode: outputMode,
                    stage: 'UPLOADED',
                    status: 'ACTIVE',
                    error_reason: null
                  }}
                />
              </div>
            )}

            {/* Error */}
            {globalError && (
              <div className="flex items-start gap-3 bg-danger/10 border border-danger/30 rounded-xl p-4" role="alert">
                <AlertTriangle className="w-5 h-5 text-danger shrink-0 mt-0.5" />
                <p className="text-danger text-sm">{globalError}</p>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 mt-6">
          {files.length > 0 ? (
            <button
              id="reset-btn"
              onClick={handleReset}
              disabled={isUploading || taskState?.status === 'ACTIVE'}
              className="btn-ghost flex-1"
            >
              {canDownload ? 'Convert Another' : 'Clear'}
            </button>
          ) : null}

          {!primaryTaskId && files.length > 0 && (
            <button
              id="convert-btn"
              onClick={handleConvert}
              disabled={isUploading}
              className="btn-primary flex-1"
            >
              {isUploading ? 'Uploading...' : `Convert ${files.length > 1 ? `${files.length} Files` : 'File'}`}
            </button>
          )}

          {canDownload && primaryTaskId && (
            <a
              id="download-btn"
              href={batchId ? getBatchDownloadUrl(batchId) : getDownloadUrl(primaryTaskId)}
              download
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              <Download className="w-4 h-4" />
              Download Result
            </a>
          )}
        </div>
      </div>

<div className="inline-flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 rounded-xl px-4 py-2 mt-4 text-amber-400/90 text-xs max-w-md mx-auto">
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
          <span>Note: Scanned documents (OCR) and raw images are not supported.</span>
        </div>
        
      {/* Stats Section */}
      {stats && (
        <div className="mt-6 flex gap-6 text-xs text-white/30 font-mono">
          <div>👥 Visitors: <span className="text-accent-400 font-semibold">{stats.visitors}</span></div>
          <div>📄 Documents Converted: <span className="text-success font-semibold">{stats.conversions}</span></div>
        </div>
      )}

      {/* Footer / Credits */}
      <footer className="mt-12 text-center flex flex-col items-center gap-3">
        <p className="text-white/20 text-xs">
          All files are processed instantly • Automatically deleted after processing. We don't store your files.
        </p>
        <div className="flex flex-col sm:flex-row items-center gap-1.5 sm:gap-4 text-xs text-white/40">
          <div>
            Developed By:{' '}
            <a
              href="https://github.com/Vineet-Singh-Chauhan"
              target="_blank"
              rel="noopener noreferrer"
              className="text-accent-400 hover:underline font-medium"
            >
              Vineet Singh Chauhan
            </a>
          </div>
          <span className="hidden sm:inline text-white/10">|</span>
          <a
            href="https://github.com/Vineet-Singh-Chauhan/mdify"
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent-400 hover:text-accent-300 hover:underline transition-colors"
          >
            📦 GitHub Repository
          </a>
          <span className="hidden sm:inline text-white/10">|</span>
          <a
            href="https://github.com/Vineet-Singh-Chauhan/mdify/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-accent-400 hover:text-accent-300 hover:underline transition-colors"
          >
            🐛 Raise an Issue (GitHub)
          </a>
        </div>
      </footer>
    </div>
  );
};
