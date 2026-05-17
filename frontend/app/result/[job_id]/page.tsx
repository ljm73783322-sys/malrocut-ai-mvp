"use client";
import { useRouter } from 'next/navigation';

export default function ResultPage({ params }: { params: { job_id: string } }) {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center space-y-12 py-10">
      <h2 className="text-5xl font-bold text-green-600">🎉 짜잔! 완벽하게 편집되었습니다.</h2>
      
      <div className="flex flex-col w-full space-y-6">
        <a 
          href={`/api/jobs/${params.job_id}/download/video`}
          className="bg-blue-600 text-white text-3xl font-bold py-6 px-8 rounded-2xl shadow-lg hover:bg-blue-700 text-center"
        >
          📹 완성된 영상 저장하기
        </a>
        <a 
          href={`/api/jobs/${params.job_id}/download/thumbnail`}
          className="bg-orange-500 text-white text-3xl font-bold py-6 px-8 rounded-2xl shadow-lg hover:bg-orange-600 text-center"
        >
          🖼️ 썸네일 사진 저장하기
        </a>
        <a 
          href={`/api/jobs/${params.job_id}/download/subtitle`}
          className="bg-gray-600 text-white text-3xl font-bold py-6 px-8 rounded-2xl shadow-lg hover:bg-gray-700 text-center"
        >
          📝 자막 파일 저장하기
        </a>
      </div>

      <button 
        onClick={() => router.push('/')}
        className="mt-8 text-2xl text-blue-500 underline"
      >
        처음으로 돌아가기
      </button>
    </div>
  );
}
