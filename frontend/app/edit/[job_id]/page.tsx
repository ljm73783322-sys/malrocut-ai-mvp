"use client";
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { editVideo, renderVideo } from '@/lib/api';

export default function EditPage({ params }: { params: { job_id: string } }) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState<any>(null);
  const router = useRouter();

  const handlePlan = async () => {
    setLoading(true);
    const result = await editVideo(params.job_id, prompt);
    setPlan(result);
    setLoading(false);
  };

  const handleRender = async () => {
    await renderVideo(params.job_id);
    router.push(`/render/${params.job_id}`);
  };

  if (plan) {
    return (
      <div className="flex flex-col items-center space-y-10 py-10">
        <h2 className="text-4xl font-bold text-gray-800">4. 편집 계획 확인</h2>
        <div className="bg-blue-50 p-8 rounded-xl w-full text-2xl text-gray-800 space-y-4 border-2 border-blue-200">
          <p>✔️ {plan.plan.subtitle_action}</p>
          <p>✔️ {plan.plan.cut_action}</p>
          <p>✔️ {plan.plan.style_action}</p>
        </div>
        <button 
          onClick={handleRender}
          className="bg-green-600 text-white text-3xl font-bold py-6 px-16 rounded-2xl shadow-lg hover:bg-green-700"
        >
          이대로 영상 만들기 시작!
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center space-y-10 py-10">
      <h2 className="text-4xl font-bold text-gray-800">3. 어떻게 편집할까요?</h2>
      <p className="text-2xl text-gray-600 text-center">
        원하시는 편집 방향을 적어주시거나, <br/>아무것도 안 적고 '알아서 편집하기'를 누르셔도 됩니다.
      </p>
      <textarea 
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="예) 화사하게 만들고 자막을 크게 달아줘"
        className="w-full h-48 p-6 text-2xl border-4 border-gray-300 rounded-xl"
      />
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
