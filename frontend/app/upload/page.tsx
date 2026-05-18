"use client";
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { uploadVideo, analyzeVideo } from '@/lib/api';

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleUpload = async () => {
    if (!file) return alert("영상을 선택해주세요.");
    setLoading(true);
    try {
      // uploadVideo는 { job_id } 만 있으면 성공 처리
      const data = await uploadVideo(file);
      const jobId = data.job_id;

      await analyzeVideo(jobId);
      router.push(`/analyze/${jobId}`);
    } catch (e: unknown) {
      // 실제 에러 메시지 표시
      const message =
        e instanceof Error
          ? e.message
          : typeof e === 'string'
          ? e
          : '알 수 없는 오류';
      alert(`업로드에 실패했습니다.\n\n오류: ${message}\n\n백엔드 서버가 실행 중인지 확인하세요.`);
      console.error('[upload] 업로드 실패:', e);
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center space-y-10 py-10">
      <h2 className="text-4xl font-bold text-gray-800">1. 영상 파일 선택</h2>
      <p className="text-2xl text-gray-600">편집할 스마트폰 영상을 골라주세요.</p>

      <input
        type="file"
        accept="video/mp4"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
        className="text-2xl p-4 border-4 border-dashed border-gray-300 rounded-xl cursor-pointer w-full text-center"
      />

      <button
        onClick={handleUpload}
        disabled={!file || loading}
        className={`text-3xl font-bold py-6 px-16 rounded-2xl shadow-lg transition ${
          file && !loading
            ? 'bg-blue-600 text-white hover:bg-blue-700'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        }`}
      >
        {loading ? '올리는 중...' : '다음으로 넘어가기'}
      </button>
    </div>
  );
}
