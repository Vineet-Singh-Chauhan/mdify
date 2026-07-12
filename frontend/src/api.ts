import type { UploadResponse, BatchUploadResponse, TaskState } from './types';

const BASE = '/api/v1';

export async function uploadFile(
  file: File,
  outputMode: string
): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  form.append('output_mode', outputMode);
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { error?: string }).error ?? 'Upload failed');
  }
  return res.json() as Promise<UploadResponse>;
}

export async function uploadBatch(
  files: File[],
  outputMode: string
): Promise<BatchUploadResponse> {
  const form = new FormData();
  files.forEach(f => form.append('files', f));
  form.append('output_mode', outputMode);
  const res = await fetch(`${BASE}/upload/batch`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { error?: string }).error ?? 'Batch upload failed');
  }
  return res.json() as Promise<BatchUploadResponse>;
}

export async function getTaskStatus(taskId: string): Promise<TaskState> {
  const res = await fetch(`${BASE}/tasks/${taskId}/status`);
  if (!res.ok) throw new Error('Task not found');
  return res.json() as Promise<TaskState>;
}

export function getDownloadUrl(taskId: string): string {
  return `${BASE}/tasks/${taskId}/download`;
}

export function getSSEUrl(taskId: string): string {
  return `${BASE}/events/${taskId}`;
}

export async function fetchStats(): Promise<{ visitors: number; conversions: number }> {
  const res = await fetch(`${BASE}/stats`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json() as Promise<{ visitors: number; conversions: number }>;
}

export async function incrementVisitorCount(): Promise<{ visitors: number; conversions: number }> {
  const res = await fetch(`${BASE}/stats/visitor`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to increment visitor count');
  return res.json() as Promise<{ visitors: number; conversions: number }>;
}
