"use client";

import Link from 'next/link';
import type { ReactNode } from 'react';
import { useCallback, useEffect, useState } from 'react';
import { API_BASE_URL, deleteJob, getJobs, type JobSummary } from '@/lib/api';

const statusStyles: Record<JobSummary['status'], string> = {
  completed: 'bg-green-100 text-green-700 border-green-200',
  failed: 'bg-red-100 text-red-700 border-red-200',
  rendering: 'bg-blue-100 text-blue-700 border-blue-200',
  pending: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  unknown: 'bg-gray-100 text-gray-700 border-gray-200',
};

function absoluteApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

function shortJobId(jobId: string): string {
  return jobId.length > 12 ? `${jobId.slice(0, 8)}...${jobId.slice(-4)}` : jobId;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value || '-';
  }
  return date.toLocaleString('ko-KR');
}

function FileFlag({ label, active }: { label: string; active: boolean }) {
  return (
    <span className={`rounded-full px-3 py-1 text-sm font-bold ${active ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-gray-100 text-gray-400 border border-gray-200'}`}>
      {label}
    </span>
  );
}

function DownloadButton({ href, enabled, children }: { href: string; enabled: boolean; children: ReactNode }) {
  const className = 'rounded-xl px-4 py-3 text-center text-base font-bold shadow-sm transition';

  if (!enabled) {
    return (
      <button
        type="button"
        disabled
        className={`${className} cursor-not-allowed bg-gray-200 text-gray-400`}
      >
        {children}
      </button>
    );
  }

  return (
    <a href={absoluteApiUrl(href)} className={`${className} bg-slate-700 text-white hover:bg-slate-800`}>
      {children}
    </a>
  );
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null);

  const loadJobs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJobs();
      setJobs(data);
    } catch (err) {
      console.error('[jobs] 작업 목록 조회 실패:', err);
      setError('작업 히스토리를 불러오지 못했습니다. 백엔드가 실행 중인지 확인해 주세요.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const handleDelete = async (jobId: string) => {
    const ok = window.confirm('이 작업을 삭제할까요? 결과 파일도 함께 삭제됩니다.');
    if (!ok) return;

    setDeleteError(null);
    setDeletingJobId(jobId);
    try {
      await deleteJob(jobId);
      await loadJobs();
    } catch (err) {
      console.error('[jobs] 작업 삭제 실패:', err);
      setDeleteError('작업 삭제에 실패했습니다. 잠시 후 다시 시도해 주세요.');
    } finally {
      setDeletingJobId(null);
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto px-4 py-10 space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-4xl font-extrabold text-gray-900">작업 히스토리</h2>
          <p className="mt-2 text-lg text-gray-600">렌더링 결과와 다운로드 파일을 한 곳에서 관리합니다.</p>
        </div>
        <Link href="/" className="rounded-xl bg-blue-600 px-5 py-3 text-center text-lg font-bold text-white shadow hover:bg-blue-700">
          홈으로 돌아가기
        </Link>
      </div>

      {loading && (
        <div className="rounded-2xl border border-blue-100 bg-blue-50 p-8 text-center text-xl font-bold text-blue-700">
          작업 기록을 불러오는 중입니다...
        </div>
      )}

      {error && !loading && (
        <div className="rounded-2xl border border-red-100 bg-red-50 p-8 text-center text-lg font-bold text-red-700">
          {error}
        </div>
      )}

      {deleteError && (
        <div className="rounded-2xl border border-red-100 bg-red-50 p-5 text-center text-base font-bold text-red-700">
          {deleteError}
        </div>
      )}

      {!loading && !error && jobs.length === 0 && (
        <div className="rounded-2xl border-2 border-dashed border-gray-300 bg-white p-12 text-center text-2xl font-bold text-gray-500">
          아직 작업 기록이 없습니다.
        </div>
      )}

      {!loading && !error && jobs.length > 0 && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
          {jobs.map((job) => (
            <article key={job.job_id} className="flex flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-lg">
              {job.has_thumbnail ? (
                <img
                  src={absoluteApiUrl(job.thumbnail_url)}
                  alt="작업 썸네일"
                  className="h-48 w-full object-cover bg-gray-100"
                />
              ) : (
                <div className="flex h-48 w-full items-center justify-center bg-gray-100 text-lg font-bold text-gray-400">
                  썸네일 없음
                </div>
              )}

              <div className="flex flex-1 flex-col gap-4 p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-bold text-gray-400">JOB ID</p>
                    <p className="font-mono text-lg font-extrabold text-gray-900" title={job.job_id}>{shortJobId(job.job_id)}</p>
                  </div>
                  <span className={`rounded-full border px-3 py-1 text-sm font-extrabold ${statusStyles[job.status]}`}>
                    {job.status}
                  </span>
                </div>

                <div>
                  <div className="mb-2 flex justify-between text-sm font-bold text-gray-600">
                    <span>Progress</span>
                    <span>{job.progress}%</span>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-gray-100">
                    <div className="h-full rounded-full bg-blue-600" style={{ width: `${job.progress}%` }} />
                  </div>
                </div>

                <div className="space-y-1 text-sm text-gray-600">
                  <p><span className="font-bold text-gray-800">생성:</span> {formatDate(job.created_at)}</p>
                  <p><span className="font-bold text-gray-800">수정:</span> {formatDate(job.updated_at)}</p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <FileFlag label="영상" active={job.has_video} />
                  <FileFlag label="썸네일" active={job.has_thumbnail} />
                  <FileFlag label="자막" active={job.has_subtitle} />
                  <FileFlag label="ZIP" active={job.has_video || job.has_thumbnail || job.has_subtitle || job.has_job_json || job.has_edit_command} />
                </div>

                <div className="mt-auto grid grid-cols-1 gap-3">
                  <Link href={job.result_url} className="rounded-xl bg-blue-600 px-4 py-3 text-center text-base font-bold text-white shadow-sm hover:bg-blue-700">
                    결과 보기
                  </Link>
                  <DownloadButton href={job.video_download_url} enabled={job.has_video}>영상 다운로드</DownloadButton>
                  <DownloadButton href={job.thumbnail_download_url} enabled={job.has_thumbnail}>썸네일 다운로드</DownloadButton>
                  <DownloadButton href={job.subtitle_download_url} enabled={job.has_subtitle}>자막 다운로드</DownloadButton>
                  <DownloadButton href={job.package_download_url} enabled={job.has_video || job.has_thumbnail || job.has_subtitle || job.has_job_json || job.has_edit_command}>
                    전체 패키지 ZIP 다운로드
                  </DownloadButton>
                  <button
                    type="button"
                    onClick={() => handleDelete(job.job_id)}
                    disabled={deletingJobId === job.job_id}
                    className="rounded-xl bg-red-600 px-4 py-3 text-base font-bold text-white shadow-sm hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-red-300"
                  >
                    {deletingJobId === job.job_id ? '삭제 중...' : '삭제'}
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
