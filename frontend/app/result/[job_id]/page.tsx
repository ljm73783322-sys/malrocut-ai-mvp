"use client";
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { getDownloadUrl, getRepresentativeThumbnailUrl, getResultPackageDownloadUrl } from '@/lib/api';

export default function ResultPage({ params }: { params: { job_id: string } }) {
  const router = useRouter();
  const [thumbnailError, setThumbnailError] = useState(false);

  const videoUrl = getDownloadUrl(params.job_id, 'video');
  const thumbnailUrl = getRepresentativeThumbnailUrl(params.job_id);
  const thumbnailDownloadUrl = getDownloadUrl(params.job_id, 'thumbnail');
  const packageDownloadUrl = getResultPackageDownloadUrl(params.job_id);

  return (
    <div className="flex flex-col items-center space-y-12 py-10 w-full max-w-5xl mx-auto px-4">
      <h2 className="text-5xl font-bold text-green-600 text-center">🎉 짜잔! 완벽하게 편집되었습니다.</h2>

      <section className="w-full bg-white rounded-2xl shadow-lg border-2 border-blue-100 p-6">
        <h3 className="text-2xl font-extrabold text-blue-900 mb-4">📹 완성 영상 미리보기</h3>
        <div className="bg-black rounded-xl overflow-hidden shadow-md flex justify-center">
          <video
            src={videoUrl}
            controls
            preload="metadata"
            className="w-full max-h-[420px]"
          />
        </div>
      </section>

      <section className="w-full bg-white rounded-2xl shadow-lg border-2 border-orange-100 p-6">
        <div className="flex flex-col gap-2 mb-5">
          <h3 className="text-2xl font-extrabold text-orange-700">🎬 유튜브 대표 썸네일</h3>
          <p className="text-lg text-gray-600">렌더링된 영상에서 자동 생성된 대표 썸네일입니다.</p>
        </div>

        {!thumbnailError ? (
          <img
            src={thumbnailUrl}
            alt="유튜브 대표 썸네일 미리보기"
            className="w-full max-w-3xl mx-auto rounded-2xl border-2 border-orange-100 shadow-lg object-cover bg-gray-100"
            onError={() => setThumbnailError(true)}
          />
        ) : (
          <div className="w-full max-w-3xl mx-auto rounded-2xl border-2 border-dashed border-gray-300 bg-gray-50 p-12 text-center text-xl text-gray-500">
            썸네일을 아직 불러올 수 없습니다.
          </div>
        )}

        <a
          href={thumbnailDownloadUrl}
          download="thumbnail.jpg"
          className="mt-6 block bg-orange-500 text-white text-2xl font-bold py-5 px-8 rounded-2xl shadow-lg hover:bg-orange-600 text-center"
        >
          썸네일 다운로드
        </a>
      </section>
      
      <div className="flex flex-col w-full space-y-6">
        <a 
          href={videoUrl}
          className="bg-blue-600 text-white text-3xl font-bold py-6 px-8 rounded-2xl shadow-lg hover:bg-blue-700 text-center"
        >
          📹 완성된 영상 저장하기
        </a>
        <a 
          href={thumbnailDownloadUrl}
          download="thumbnail.jpg"
          className="bg-orange-500 text-white text-3xl font-bold py-6 px-8 rounded-2xl shadow-lg hover:bg-orange-600 text-center"
        >
          🖼️ 썸네일 사진 저장하기
        </a>
        <a 
          href={packageDownloadUrl}
          className="bg-purple-600 text-white text-3xl font-bold py-6 px-8 rounded-2xl shadow-lg hover:bg-purple-700 text-center"
        >
          📦 전체 패키지 ZIP 다운로드
        </a>
        <a 
          href={getDownloadUrl(params.job_id, 'subtitle')}
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
