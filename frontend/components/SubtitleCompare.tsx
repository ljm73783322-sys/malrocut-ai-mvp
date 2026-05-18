"use client";

import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "@/lib/api";

interface SubtitleCompareProps {
  jobId: string;
  /** edit_command에서 전달받은 자막 관련 정보 */
  addSubtitle?: boolean;
  subtitleText?: string;
  subtitleSize?: string;
  subtitleLanguage?: string;
}

const DEFAULT_SUBTITLE = "말로컷 AI로 새롭게 편집된 영상입니다";

const LANG_LABELS: Record<string, string> = {
  ko: "한국어",
  en: "영어",
  ja: "일본어",
};

export default function SubtitleCompare({
  jobId,
  addSubtitle = true,
  subtitleText,
  subtitleSize = "large",
  subtitleLanguage = "ko",
}: SubtitleCompareProps) {
  const [originalSub, setOriginalSub] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchOriginal = async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/api/jobs/${jobId}/download/original_subtitle`
        );
        if (res.ok) {
          const text = await res.text();
          // 빈 파일이나 너무 짧은 응답은 무시
          if (text && text.trim().length > 5) {
            setOriginalSub(text);
          }
        }
      } catch {
        // 네트워크 오류 — 무시
      } finally {
        setLoading(false);
      }
    };
    fetchOriginal();
  }, [jobId]);

  // 새 자막 텍스트 결정
  const newSubtitleDisplay = subtitleText?.trim() || DEFAULT_SUBTITLE;
  const sizeLabel = subtitleSize === "large" ? "크게" : "작게";
  const langLabel = LANG_LABELS[subtitleLanguage] || "한국어";

  if (loading) {
    return (
      <div className="w-full bg-white rounded-2xl shadow-lg p-6 mb-8 border-2 border-orange-100">
        <div className="flex justify-center py-6">
          <div className="w-6 h-6 border-4 border-orange-300 border-t-orange-600 rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-white rounded-2xl shadow-lg p-6 mb-8 border-2 border-orange-100">
      <h2 className="text-2xl font-extrabold text-orange-900 mb-6 flex items-center">
        <span className="bg-orange-100 text-orange-600 px-3 py-1 rounded-lg mr-3 text-lg">
          자막 확인
        </span>
        자막 변경 내용
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* ── 원본 자막 ─────────────────────────────────── */}
        <div className="bg-gray-50 rounded-xl p-5 border border-gray-200">
          <h3 className="text-lg font-bold text-gray-700 mb-3 border-b pb-2">
            📄 원본 자막
          </h3>
          {originalSub ? (
            <pre className="whitespace-pre-wrap text-gray-600 font-sans text-sm h-48 overflow-y-auto">
              {originalSub}
            </pre>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-400 text-lg">
              원본 자막이 아직 추출되지 않았습니다.
              <br />
              <span className="text-sm text-gray-300 mt-1 block">
                (Whisper 음성 인식은 추후 지원 예정)
              </span>
            </div>
          )}
        </div>

        {/* ── 새로운 자막 ────────────────────────────────── */}
        <div className="bg-orange-50 rounded-xl p-5 border border-orange-200">
          <h3 className="text-lg font-bold text-orange-800 mb-3 border-b border-orange-200 pb-2">
            ✏️ 새로운 자막
          </h3>
          {addSubtitle ? (
            <div className="h-48 flex flex-col justify-center">
              {/* 실제 자막 미리보기 */}
              <div className="bg-black/80 rounded-xl p-4 mb-4">
                <p className={`text-center font-bold text-white ${
                  subtitleSize === "large" ? "text-2xl" : "text-base"
                }`}>
                  {newSubtitleDisplay}
                </p>
              </div>
              {/* 설정 요약 */}
              <div className="text-sm text-orange-600 space-y-1">
                <p>• 크기: <strong>{sizeLabel}</strong></p>
                <p>• 언어: <strong>{langLabel}</strong></p>
                <p>• 위치: <strong>하단 중앙</strong></p>
              </div>
            </div>
          ) : (
            <div className="h-48 flex items-center justify-center text-orange-400 text-lg">
              자막 추가가 요청되지 않았습니다.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
