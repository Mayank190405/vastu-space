import { CaptureSessionRecord, PipelineStageRecord } from '../../types';

export interface PipelineJob {
  id: string; stage: string; progress_percentage: number;
  error_code?: string; error_message?: string; updated_at: string;
}
export interface PipelineLog { id: string; created_at: string; stage: string; log_level: string; message: string }
export interface ScanPipeline { session: CaptureSessionRecord; stages: PipelineStageRecord[]; job?: PipelineJob }

const names: Record<string, string> = {
  PROJECT_CREATED: 'Project created', ROOM_CREATED: 'Space assigned', QR_SESSION_GENERATED: 'QR ready',
  DEVICE_CONNECTED: 'Device connected', SESSION_AUTHORIZED: 'Session authorized', ARKIT_CAPTURE_RUNNING: 'Recording',
  LOCAL_AI_ANALYSIS: 'On-device analysis', CAPTURE_VALIDATION: 'Capture validation', UPLOADING: 'Uploading video',
  UPLOAD_VERIFIED: 'Video verified in storage', VIEWER_PUBLISHING: 'Publishing viewer', COMPLETED: 'Completed',
};
export const stageLabel = (name: string) => names[name] || (name.startsWith('RECONSTRUCTION_') ? `Reconstruction · stage ${name.slice(-2)}` : name.replace(/_/g, ' ').toLowerCase());
export const currentStages = (scan: ScanPipeline) => scan.stages.filter(s => !s.job_id || !scan.session.job_id || s.job_id === scan.session.job_id);
export function pipelineState(scan: ScanPipeline) {
  const stages = currentStages(scan);
  const latest = (statuses: string[]) => stages.filter(s => statuses.includes(s.status)).sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))[0];
  if (scan.job?.stage === 'failed') return { label: 'Failed', tone: 'failed', stage: latest(['RETRYING', 'RUNNING']) || latest(['FAILED']) };
  if (scan.session.viewer_url && scan.session.status === 'COMPLETED' && scan.job?.stage === 'completed') return { label: 'Viewer ready', tone: 'complete', stage: latest(['COMPLETED']) };
  const failed = latest(['FAILED']);
  if (failed) return { label: 'Failed', tone: 'failed', stage: failed };
  const retrying = latest(['RETRYING']);
  if (retrying) return { label: 'Retrying', tone: 'retrying', stage: retrying };
  const running = latest(['RUNNING']);
  if (running) return { label: stageLabel(running.stage_name), tone: 'running', stage: running };
  if (scan.job?.stage === 'queued') return { label: 'Queued for processing', tone: 'queued', stage: undefined };
  if (scan.session.job_id) return { label: 'Processing', tone: 'running', stage: latest(['COMPLETED']) };
  if (scan.session.upload_verified_at) return { label: 'Video verified · awaiting processing', tone: 'queued', stage: latest(['COMPLETED']) };
  if (scan.session.upload_id) return { label: 'Uploading video', tone: 'running', stage: undefined };
  return { label: scan.session.status.replace(/_/g, ' ').toLowerCase(), tone: 'pending', stage: undefined };
}
export const isSubmitted = (s: CaptureSessionRecord) => Boolean(s.upload_id || s.capture_id || s.job_id || s.upload_verified_at);
export const terminalPipeline = (scan: ScanPipeline) => ['failed', 'completed'].includes(scan.job?.stage || '') || (!scan.session.job_id && ['REVOKED', 'EXPIRED', 'COMPLETED'].includes(scan.session.status));
export const toneClasses: Record<string, string> = {
  failed: 'bg-rose-50 text-rose-700 border-rose-200', complete: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  running: 'bg-blue-50 text-blue-700 border-blue-200', retrying: 'bg-amber-50 text-amber-800 border-amber-200',
  queued: 'bg-amber-50 text-amber-800 border-amber-200', pending: 'bg-stone-100 text-stone-600 border-stone-200',
};
