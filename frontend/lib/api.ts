import axios, { AxiosError } from 'axios';

// 백엔드 주소 고정 (Next.js 프록시 우회)
const BASE_URL = 'http://127.0.0.1:8000';

// 컴포넌트에서 직접 URL을 구성할 때 사용
export const API_BASE_URL = BASE_URL;

const api = axios.create({
  baseURL: `${BASE_URL}/api`,
});

// ─── 업로드 ────────────────────────────────────────────────────────────────

export const uploadVideo = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file); // 필드명 'file' 고정

  const url = `${BASE_URL}/api/jobs/upload`;
  console.log('[api] 업로드 요청 URL:', url);

  // Content-Type 헤더 직접 지정 금지 → fetch가 boundary 자동 설정
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  console.log('[api] 업로드 응답 status:', response.status);

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const errBody = await response.json();
      console.log('[api] 업로드 에러 body:', errBody);
      detail = errBody?.detail ?? JSON.stringify(errBody) ?? detail;
    } catch {
      // JSON 파싱 실패 시 status 코드만 사용
    }
    throw new Error(detail);
  }

  const data = await response.json();
  console.log('[api] 업로드 응답 body:', data);

  // { job_id: "..." } 만 있어도 성공
  if (!data.job_id) {
    throw new Error('응답에 job_id가 없습니다: ' + JSON.stringify(data));
  }

  return data as { job_id: string };
};

// ─── 분석 ────────────────────────────────────────────────────────────────

export const analyzeVideo = async (jobId: string) => {
  const res = await api.post(`/jobs/${jobId}/analyze`);
  return res.data;
};

export const getAnalysis = async (jobId: string) => {
  const res = await api.get(`/jobs/${jobId}/analysis`);
  return res.data;
};

// ─── 편집 ────────────────────────────────────────────────────────────────

export const editVideo = async (jobId: string, prompt: string) => {
  const res = await api.post(`/jobs/${jobId}/edit`, { prompt });
  return res.data;
};

// ─── 렌더링 ──────────────────────────────────────────────────────────────

export const renderVideo = async (jobId: string) => {
  const res = await api.post(`/jobs/${jobId}/render`);
  return res.data;
};

// ─── 상태 조회 ────────────────────────────────────────────────────────────


export interface JobStatusResponse {
  job_id: string;
  status: string;
  progress: number;
  error?: string | null;
}

export const getStatus = async (jobId: string): Promise<JobStatusResponse> => {
  const res = await api.get(`/jobs/${jobId}/status`);
  return res.data;
};

// ─── 타임라인 썸네일 ──────────────────────────────────────────────────────

export interface TimelineThumbnail {
  time: number;
  url: string;
}

export interface TimelineThumbnailsResponse {
  job_id: string;
  duration: number;
  thumbnails: TimelineThumbnail[];
}

export const getTimelineThumbnails = async (jobId: string): Promise<TimelineThumbnailsResponse> => {
  const res = await api.get(`/jobs/${jobId}/timeline-thumbnails`);
  return res.data;
};


// ─── 작업 히스토리 ──────────────────────────────────────────────────────

export interface JobSummary {
  job_id: string;
  status: 'completed' | 'failed' | 'rendering' | 'pending' | 'unknown';
  progress: number;
  created_at: string;
  updated_at: string;
  has_video: boolean;
  has_thumbnail: boolean;
  has_subtitle: boolean;
  has_job_json: boolean;
  has_edit_command: boolean;
  video_download_url: string;
  thumbnail_download_url: string;
  subtitle_download_url: string;
  package_download_url: string;
  result_url: string;
  thumbnail_url: string;
}

export interface DeleteJobResponse {
  ok: boolean;
  deleted: boolean;
  job_id: string;
}

export const getJobs = async (): Promise<JobSummary[]> => {
  const res = await api.get('/jobs');
  return res.data;
};

export const deleteJob = async (jobId: string): Promise<DeleteJobResponse> => {
  const res = await api.delete(`/jobs/${jobId}`);
  return res.data;
};


// ─── 썸네일 편집 ──────────────────────────────────────────────────────────

export interface ThumbnailTextPayload {
  text: string;
  font_size: number;
  text_color: string;
  background_color: string;
  position: 'center' | 'top' | 'bottom';
  reset_base?: boolean;
}

export interface ThumbnailUpdateResponse {
  ok: boolean;
  job_id: string;
  thumbnail_url: string;
}

export const uploadJobThumbnail = async (jobId: string, file: File): Promise<ThumbnailUpdateResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const res = await api.post(`/jobs/${jobId}/thumbnail/upload`, formData);
  return res.data;
};

export const updateJobThumbnailText = async (
  jobId: string,
  payload: ThumbnailTextPayload,
): Promise<ThumbnailUpdateResponse> => {
  const res = await api.post(`/jobs/${jobId}/thumbnail/text`, payload);
  return res.data;
};

// ─── URL 생성 헬퍼 ────────────────────────────────────────────────────────

/** 원본 영상 스트리밍 URL */
export const getInputVideoUrl = (jobId: string): string =>
  `${API_BASE_URL}/api/jobs/${jobId}/download/original_video`;

/** 타임라인 썸네일 이미지의 절대 URL (상대 경로를 절대로 변환) */
export const getThumbnailAbsoluteUrl = (relativeUrl: string): string =>
  `${API_BASE_URL}${relativeUrl}`;


/** 결과물 다운로드 URL */
export const getDownloadUrl = (jobId: string, fileType: "video" | "thumbnail" | "subtitle"): string =>
  `${API_BASE_URL}/api/jobs/${jobId}/download/${fileType}`;

/** 대표 썸네일 미리보기 URL */
export const getRepresentativeThumbnailUrl = (jobId: string): string =>
  `${API_BASE_URL}/api/jobs/${jobId}/thumbnail`;


/** 결과 패키지 ZIP 다운로드 URL */
export const getResultPackageDownloadUrl = (jobId: string): string =>
  `${API_BASE_URL}/api/jobs/${jobId}/download/package`;
