"use client";

import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "@/lib/api";

interface SubtitleCompareProps {
  jobId: string;
}

export default function SubtitleCompare({ jobId }: SubtitleCompareProps) {
  const [originalSub, setOriginalSub] = useState<string | null>(null);
  const [editedSub, setEditedSub] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSubtitles = async () => {
      try {
        // 원본 자막 시도
        const origRes = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/download/original_subtitle`);
        if (origRes.ok) {
          setOriginalSub(await origRes.text());
        } else {
          setOriginalSub(null);
        }

        // 수정 자막 시도
        const editRes = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/download/subtitle`);
        if (editRes.ok) {
          setEditedSub(await editRes.text());
        } else {
          setEditedSub(null);
        }
      } catch (err) {
        console.error("자막 로드 실패:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchSubtitles();
  }, [jobId]);

  if (loading) return null;

  return (
    <div className="w-full bg-white rounded-2xl shadow-lg p-6 mb-8 border-2 border-orange-100">
      <h2 className="text-2xl font-extrabold text-orange-900 mb-6 flex items-center">
        <span className="bg-orange-100 text-orange-600 px-3 py-1 rounded-lg mr-3 text-lg">자막 확인</span>
        자막 변경 내용
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 원본 자막 */}
        <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
          <h3 className="text-lg font-bold text-gray-700 mb-3 border-b pb-2">원본 자막</h3>
          {originalSub ? (
            <pre className="whitespace-pre-wrap text-gray-600 font-sans text-sm h-48 overflow-y-auto">
              {originalSub}
            </pre>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400">
              원본 자막이 아직 추출되지 않았습니다.
            </div>
          )}
        </div>

        {/* 수정 자막 */}
        <div className="bg-orange-50 rounded-xl p-4 border border-orange-200">
          <h3 className="text-lg font-bold text-orange-800 mb-3 border-b border-orange-200 pb-2">새로운 자막</h3>
          {editedSub ? (
            <pre className="whitespace-pre-wrap text-orange-900 font-sans text-sm h-48 overflow-y-auto font-bold">
              {editedSub}
            </pre>
          ) : (
            <div className="h-48 flex items-center justify-center text-orange-300">
              추가될 새 자막이 없습니다.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
