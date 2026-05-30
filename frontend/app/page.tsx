import Link from 'next/link';

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center space-y-12 py-12">
      <h2 className="text-3xl font-semibold text-gray-800 text-center leading-relaxed">
        안녕하세요!<br/>
        영상을 올리고 클릭만 하시면<br/>
        자동으로 멋지게 편집해 드립니다.
      </h2>
      <div className="flex flex-col sm:flex-row gap-4 items-center">
        <Link href="/upload" className="bg-blue-600 text-white text-3xl font-bold py-6 px-12 rounded-2xl shadow-lg hover:bg-blue-700 transition">
          시작하기 (영상 올리기)
        </Link>
        <Link href="/jobs" className="bg-white text-blue-600 border-2 border-blue-200 text-2xl font-bold py-5 px-8 rounded-2xl shadow hover:bg-blue-50 transition">
          작업 히스토리 보기
        </Link>
      </div>
      <Link href="/upload" className="bg-blue-600 text-white text-3xl font-bold py-6 px-12 rounded-2xl shadow-lg hover:bg-blue-700 transition">
        시작하기 (영상 올리기)
      </Link>
      <a
        href="http://127.0.0.1:8000/api/health"
        target="_blank"
        rel="noopener noreferrer"
        className="text-sm text-gray-500 underline underline-offset-4 hover:text-gray-800"
      >
        백엔드 상태 확인
      </a>
    </div>
  );
}
