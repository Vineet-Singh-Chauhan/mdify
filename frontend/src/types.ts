export type OutputMode = 'standalone' | 'package';

export type PipelineStage =
  | 'UPLOADED'
  | 'SCANNING'
  | 'PARSING'
  | 'RESOLVING_ASSETS'
  | 'PACKAGING';

export type TaskStatus = 'PENDING' | 'ACTIVE' | 'SUCCESS' | 'FAILURE';

export interface TaskState {
  task_id: string;
  batch_id: string | null;
  original_name: string;
  output_mode: OutputMode;
  stage: PipelineStage;
  status: TaskStatus;
  error_reason: string | null;
}

export interface UploadResponse {
  task_id: string;
  original_name: string;
  output_mode: string;
  status: string;
}

export interface BatchUploadResponse {
  batch_id: string;
  task_ids: string[];
  status: string;
}

export interface StatsState {
  visitors: number;
  conversions: number;
}
