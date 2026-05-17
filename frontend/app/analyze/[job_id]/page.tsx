"use client";
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getStatus, getAnalysis } from '@/lib/api';

export default function AnalyzePage({ params }: { params: { job_id: string } }) {
  const [status, setStatus] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const router = useRouter();

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const st = await getStatus(params.job_id);
        setStatus(st);
        if (st.status === 'analyzed') {
          clearInterval(interval);
          const data = await getAnalysis(params.job_id);
          setAnalysis(data);
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [params.job_id]);

  if (!analysis) {
    return (
      <div className="flex flex-col items-center justify-center space-y-6 py-20">
        <div className="animate-spin rounded-full h-32 w-32 border-b-8 border-blue-600"></div>
        <h2 className="text-4xl font-bold text-gray-800">영상을 분석하고 있습니다...</h2>
        <p className="text-2xl text-gray-600">잠시만 기다려주세요.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center space-y-10 py-10">
      <h2 className="text-4xl font-bold text-gray-800">2. 분석 완료!</h2>
      <div className="bg-gray-100 p-8 rounded-xl w-full text-2xl text-gray-700 space-y-4">
        <p><strong>발견된 음성:</strong> {analysis.has_audio ? "네" : "아니오"}</p>
        <p><strong>기존 자막:</strong> {analysis.has_subtitles ? "발견됨" : "없음"}</p>
        <p><strong>추출된 대본 일부:</strong> {analysis.transcript_preview}</p>
      </div>
      <button 
        onClick={() => router.push(`/edit/${params.job_id}`)}
        className="bg-blue-600 text-white text-3xl font-bold py-6 px-16 rounded-2xl shadow-lg hover:bg-blue-700"
      >
        어떻게 편집할지 적기
      </button>
    </div>
  );
}
