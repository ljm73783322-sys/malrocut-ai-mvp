"use client";
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getStatus } from '@/lib/api';

export default function RenderPage({ params }: { params: { job_id: string } }) {
  const [progress, setProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const st = await getStatus(params.job_id);
        if (st.progress !== undefined) {
          setProgress(st.progress);
        }
        if (st.status === 'completed') {
          clearInterval(interval);
          router.push(`/result/${params.job_id}`);
        } else if (st.status === 'failed' || st.status === 'error') {
          clearInterval(interval);
          setErrorMessage(st.error || '렌더링 중 오류가 발생했습니다.');
        }
      } catch (e) {
        console.error(e);
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [params.job_id]);

  return (
    <div className="flex flex-col items-center justify-center space-y-12 py-20">
      <h2 className="text-4xl font-bold text-gray-800">열심히 영상을 만들고 있습니다!</h2>
      <div className="w-full bg-gray-200 rounded-full h-12 overflow-hidden border-2 border-gray-300">
        <div 
          className="bg-blue-600 h-12 transition-all duration-500 ease-in-out" 
          style={{ width: `${progress}%` }}
        ></div>
      </div>
      <p className="text-4xl font-bold text-blue-600">{progress}%</p>
      {errorMessage ? (
        <div className="w-full bg-red-50 border-2 border-red-200 rounded-xl p-6 text-center">
          <p className="text-2xl font-bold text-red-600 mb-2">렌더링에 실패했습니다.</p>
          <p className="text-lg text-red-500">{errorMessage}</p>
        </div>
      ) : (
        <p className="text-2xl text-gray-500">조금만 기다려주시면 완성됩니다.</p>
      )}
    </div>
  );
}
