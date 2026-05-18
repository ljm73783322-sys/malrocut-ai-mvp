"use client";
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { editVideo, renderVideo } from '@/lib/api';
import TimelinePreview from '@/components/TimelinePreview';
import SubtitleCompare from '@/components/SubtitleCompare';

// 백엔드 응답 타입
interface EditCommand {
  add_subtitle: boolean;
  cover_subtitle_area: boolean;
  subtitle_size: string;
  subtitle_language: string;
  zoom: number;
  brightness: number | null;
  contrast: number | null;
  cut_silence: boolean;
  clip_reorder?: {
    enabled: boolean;
    clips: any[];
  };
}

interface EditResult {
  job_id: string;
  prompt: string;
  edit_command: EditCommand;
  plan_items: string[];
}

export default function EditPage({ params }: { params: { job_id: string } }) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<EditResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handlePlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await editVideo(params.job_id, prompt) as EditResult;
      setResult(data);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '편집 계획 생성 실패';
      setError(msg);
      console.error('[edit] 편집 계획 오류:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleRender = async () => {
    try {
      await renderVideo(params.job_id);
      router.push(`/render/${params.job_id}`);
    } catch (e) {
      console.error('[edit] 렌더링 시작 실패:', e);
    }
  };

  // ── 편집 계획 확인 화면 ─────────────────────────────────────────────────
  if (result) {
    const planItems: string[] = result.plan_items?.length
      ? result.plan_items
      : ["기본 설정으로 편집합니다."];

    return (
      <div className="flex flex-col items-center space-y-10 py-10 w-full max-w-5xl mx-auto px-4">
        <h2 className="text-4xl font-bold text-gray-800">4. 편집 계획 확인</h2>

        {/* 사용자 입력 프롬프트 표시 */}
        <div className="bg-gray-100 p-6 rounded-xl w-full text-xl text-gray-600 border-2 border-gray-200">
          <p className="font-semibold text-gray-500 mb-1">입력하신 편집 요청:</p>
          <p className="text-2xl text-gray-800">
            {result.prompt?.trim() ? `"${result.prompt}"` : '(직접 입력 없음 — 기본 설정 적용)'}
          </p>
        </div>

        {/* 편집 계획 항목 */}
        <div className="bg-blue-50 p-8 rounded-xl w-full text-2xl text-gray-800 space-y-4 border-2 border-blue-200">
          {planItems.map((item, idx) => (
            <p key={idx}>✔️ {item}</p>
          ))}
        </div>

        {/* 클립 순서 변경 시 타임라인 프리뷰 표시 */}
        {result.edit_command.clip_reorder?.enabled && (
          <TimelinePreview 
            jobId={params.job_id} 
            clips={result.edit_command.clip_reorder.clips} 
          />
        )}

        {/* 자막 비교 표시 */}
        <SubtitleCompare
          jobId={params.job_id}
          addSubtitle={result.edit_command.add_subtitle}
          subtitleSize={result.edit_command.subtitle_size}
          subtitleLanguage={result.edit_command.subtitle_language}
        />

        <button
          onClick={handleRender}
          className="bg-green-600 text-white text-3xl font-bold py-6 px-16 rounded-2xl shadow-lg hover:bg-green-700"
        >
          이대로 영상 만들기 시작!
        </button>
      </div>
    );
  }

  // ── 편집 프롬프트 입력 화면 ─────────────────────────────────────────────
  return (
    <div className="flex flex-col items-center space-y-10 py-10 w-full max-w-4xl mx-auto px-4">
      <h2 className="text-4xl font-bold text-gray-800">3. 어떻게 편집할까요?</h2>
      <p className="text-2xl text-gray-600 text-center">
        원하시는 편집 방향을 적어주시거나, <br/>아무것도 안 적고 '알아서 편집하기'를 누르셔도 됩니다.
      </p>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="예) 화사하게 만들고 자막을 크게 달아줘. 1~3초랑 6~8초 순서도 바꿔줘."
        className="w-full h-48 p-6 text-2xl border-4 border-gray-300 rounded-xl"
      />
      {error && (
        <p className="text-red-500 text-xl">오류: {error}</p>
      )}
      <button
        onClick={handlePlan}
        disabled={loading}
        className="bg-blue-600 text-white text-3xl font-bold py-6 px-16 rounded-2xl shadow-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? '계획 짜는 중...' : '알아서 편집하기'}
      </button>
    </div>
  );
}
