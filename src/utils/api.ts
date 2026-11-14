import { FullDashboardPayload, CommentRecord } from '../types';

const API_BASE = '/api';

export interface DashboardResponse {
  has_data: boolean;
  snapshot_id?: number;
  cutoff_date?: string;
  uploaded_at?: string;
  data: FullDashboardPayload | null;
  message?: string;
}

export interface UploadResponse {
  success: boolean;
  message?: string;
  error?: string;
  snapshot_id?: number;
  cutoff_date?: string;
  payload?: FullDashboardPayload;
}

export interface SnapshotSummary {
  id: number;
  title: string;
  uploaded_at: string;
  uploaded_by_name: string;
  cutoff_date: string | null;
  status: string;
  is_active: boolean;
  files_count: number;
  error_message: string;
}

/**
 * Fetch the centralized active production report from the Django + PostgreSQL backend.
 */
export async function fetchActiveDashboard(): Promise<DashboardResponse> {
  const resp = await fetch(`${API_BASE}/dashboard/`, {
    headers: { Accept: 'application/json' },
  });
  if (!resp.ok) {
    throw new Error(`Failed to fetch dashboard: ${resp.status} ${resp.statusText}`);
  }
  return resp.json();
}

/**
 * Upload the Excel files package (.zip or multiple .xlsx) to the Django backend.
 */
export async function uploadReportPackage(formData: FormData): Promise<UploadResponse> {
  const resp = await fetch(`${API_BASE}/reports/upload/`, {
    method: 'POST',
    body: formData,
  });
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.error || `Upload failed with status ${resp.status}`);
  }
  return data;
}

/**
 * Fetch all comments from PostgreSQL.
 */
export async function fetchComments(): Promise<CommentRecord[]> {
  const resp = await fetch(`${API_BASE}/comments/`, {
    headers: { Accept: 'application/json' },
  });
  if (!resp.ok) {
    throw new Error(`Failed to load comments: ${resp.statusText}`);
  }
  return resp.json();
}

/**
 * Create or update a comment in PostgreSQL.
 */
export async function saveCommentApi(comment: Partial<CommentRecord>): Promise<CommentRecord> {
  const resp = await fetch(`${API_BASE}/comments/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(comment),
  });
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.error || 'Failed to save comment');
  }
  return data.comment;
}

/**
 * Delete a comment from PostgreSQL.
 */
export async function deleteCommentApi(commentId: string): Promise<void> {
  const resp = await fetch(`${API_BASE}/comments/${commentId}/`, {
    method: 'DELETE',
  });
  if (!resp.ok) {
    throw new Error(`Failed to delete comment: ${resp.statusText}`);
  }
}

/**
 * Returns the download URL for exporting comments into formatted Excel.
 */
export function getCommentsExcelExportUrl(): string {
  return `${API_BASE}/comments/export/`;
}

/**
 * List all historical report snapshots.
 */
export async function fetchSnapshots(): Promise<SnapshotSummary[]> {
  const resp = await fetch(`${API_BASE}/reports/`, {
    headers: { Accept: 'application/json' },
  });
  if (!resp.ok) {
    throw new Error(`Failed to fetch report history: ${resp.statusText}`);
  }
  return resp.json();
}

/**
 * Activate a historical snapshot plant-wide.
 */
export async function activateSnapshot(id: number): Promise<void> {
  const resp = await fetch(`${API_BASE}/reports/${id}/activate/`, {
    method: 'POST',
  });
  if (!resp.ok) {
    throw new Error(`Failed to activate report #${id}`);
  }
}

