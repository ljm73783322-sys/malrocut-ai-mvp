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

export const getStatus = async (jobId: string) => {
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

// ─── URL 생성 헬퍼 ────────────────────────────────────────────────────────

/** 원본 영상 스트리밍 URL */
export const getInputVideoUrl = (jobId: string): string =>
  `${API_BASE_URL}/api/jobs/${jobId}/download/original_video`;

/** 타임라인 썸네일 이미지의 절대 URL (상대 경로를 절대로 변환) */
export const getThumbnailAbsoluteUrl = (relativeUrl: string): string =>
  `${API_BASE_URL}${relativeUrl}`;
