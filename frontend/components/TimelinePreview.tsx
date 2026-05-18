"use client";

import React, { useRef, useState } from "react";
import { getInputVideoUrl } from "@/lib/api";
import ThumbnailTimeline from "@/components/ThumbnailTimeline";

interface Clip {
  id: string;
  source_start: number;
  source_end: number;
  new_order: number;
}

interface TimelinePreviewProps {
  jobId: string;
  clips?: Clip[];
  editCommand?: any;
}

interface Segment {
  id: string;
  label: string;
  start: number;
  end: number;
  color: string;
  textColor: string;
}

type VideoState = "loading" | "ready" | "error";

const DEFAULT_SUBTITLE = "말로컷 AI로 새롭게 편집된 영상입니다";

export default function TimelinePreview({ jobId, clips = [], editCommand }: TimelinePreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [duration, setDuration] = useState<number>(0);
  const [videoState, setVideoState] = useState<VideoState>("loading");
  const [activeSegment, setActiveSegment] = useState<Segment | null>(null);
  const [playingLabel, setPlayingLabel] = useState<string>("");
  const clipA = clips[0] ?? null;
  const clipB = clips[1] ?? null;

  // ── 이벤트 핸들러 ─────────────────────────────────────────────────────
  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      const d = videoRef.current.duration;
      if (!d || isNaN(d) || d <= 0) {
        setVideoState("error");
      } else {
        setDuration(d);
        setVideoState("ready");
      }
    }
  };

  const handleError = () => {
    setVideoState("error");
  };

  const handleTimeUpdate = () => {
    if (videoRef.current && activeSegment) {
      if (videoRef.current.currentTime >= activeSegment.end) {
        videoRef.current.pause();
        setActiveSegment(null);
        setPlayingLabel("");
      }
    }
  };

  const playSegment = (seg: Segment) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seg.start;
      videoRef.current.play();
      setActiveSegment(seg);
      setPlayingLabel(seg.label);
    }
  };

  // ── 구간 분할 ────────────────────────────────────────────────────────
  const buildSegments = () => {
    if (!clipA || !clipB || duration === 0) return { original: [], modified: [] };

    const s1 = clipA.source_start;
    const e1 = Math.min(clipA.source_end, duration);
    const s2 = clipB.source_start;
    const e2 = Math.min(clipB.source_end, duration);

    const makeSeg = (start: number, end: number, label: string, color: string, textColor: string): Segment | null => {
      if (end - start > 0.05) {
        return { id: `${start}-${end}`, start, end, label, color, textColor };
      }
      return null;
    };

    const original: Segment[] = [
      makeSeg(0, s1, "기본", "#e5e7eb", "#6b7280"),
      makeSeg(s1, e1, "A", "#93c5fd", "#1e3a5f"),
      makeSeg(e1, s2, "기본", "#e5e7eb", "#6b7280"),
      makeSeg(s2, e2, "B", "#86efac", "#14532d"),
      makeSeg(e2, duration, "기본", "#e5e7eb", "#6b7280"),
    ].filter(Boolean) as Segment[];

    const modified: Segment[] = [
      makeSeg(0, s1, "기본", "#e5e7eb", "#6b7280"),
      makeSeg(s2, e2, "B", "#86efac", "#14532d"),
      makeSeg(e1, s2, "기본", "#e5e7eb", "#6b7280"),
      makeSeg(s1, e1, "A", "#93c5fd", "#1e3a5f"),
      makeSeg(e2, duration, "기본", "#e5e7eb", "#6b7280"),
    ].filter(Boolean) as Segment[];

    return { original, modified };
  };

  const { original, modified } = buildSegments();

  // ── 타임라인 바 렌더링 ────────────────────────────────────────────────
  const renderTimeline = (title: string, segments: Segment[]) => {
    const totalDur = segments.reduce((acc, s) => acc + (s.end - s.start), 0);
    return (
      <div className="mb-5">
        <h3 className="text-xl font-bold mb-2 text-gray-700">{title}</h3>
        <div className="flex w-full h-14 rounded-xl overflow-hidden border-2 border-gray-300 shadow-sm">
          {segments.map((seg, i) => {
            const widthPct = totalDur > 0 ? ((seg.end - seg.start) / totalDur) * 100 : 0;
            const isActive = activeSegment?.id === seg.id;
            return (
              <div
                key={i}
                onClick={() => playSegment(seg)}
                className="h-full flex items-center justify-center cursor-pointer transition-all border-r border-white/50"
                style={{
                  width: `${widthPct}%`,
                  backgroundColor: seg.color,
                  color: seg.textColor,
                  outline: isActive ? "3px solid #2563eb" : "none",
                  outlineOffset: "-3px",
                }}
                title={`${seg.label} | ${seg.start.toFixed(1)}초 ~ ${seg.end.toFixed(1)}초 클릭하면 재생`}
              >
                <span className="text-xs sm:text-sm font-bold whitespace-nowrap px-1">
                  {seg.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // ── 구간 버튼 ────────────────────────────────────────────────────────
  const renderSegmentButtons = () => {
    if (!clipA || !clipB || duration === 0) return null;

    const buttons = [
      {
        label: `▶ 구간 A (${clipA.source_start}~${clipA.source_end}초) 보기`,
        seg: { id: "a", label: "구간 A", start: clipA.source_start, end: Math.min(clipA.source_end, duration), color: "#93c5fd", textColor: "#1e3a5f" },
        bg: "bg-blue-100 hover:bg-blue-200 text-blue-800 border-blue-300",
      },
      {
        label: `▶ 구간 B (${clipB.source_start}~${clipB.source_end}초) 보기`,
        seg: { id: "b", label: "구간 B", start: clipB.source_start, end: Math.min(clipB.source_end, duration), color: "#86efac", textColor: "#14532d" },
        bg: "bg-green-100 hover:bg-green-200 text-green-800 border-green-300",
      },
    ];

    return (
      <div className="flex flex-col sm:flex-row gap-3 mt-4">
        {buttons.map((btn, i) => (
          <button
            key={i}
            onClick={() => playSegment(btn.seg)}
            className={`flex-1 text-lg font-bold py-4 px-6 rounded-xl border-2 transition-colors ${btn.bg}`}
          >
            {btn.label}
          </button>
        ))}
      </div>
    );
  };

  // ── 비디오 URL ────────────────────────────────────────────────────────
  const videoUrl = getInputVideoUrl(jobId);

  // ── 메인 렌더링 ───────────────────────────────────────────────────────
  return (
    <div className="w-full bg-white rounded-2xl shadow-lg p-6 mb-8 border-2 border-blue-100">
      <h2 className="text-2xl font-extrabold text-blue-900 mb-4 flex items-center">
        <span className="bg-blue-100 text-blue-600 px-3 py-1 rounded-lg mr-3 text-lg">미리보기</span>
        컷 순서 변경 확인
      </h2>

      {/* 비디오 플레이어 */}
      <div className="mb-4 bg-black rounded-xl overflow-hidden shadow-md flex justify-center relative">
        <video
          ref={videoRef}
          src={videoUrl}
          controls
          preload="metadata"
          className="max-h-[300px] w-auto"
          onLoadedMetadata={handleLoadedMetadata}
          onError={handleError}
          onTimeUpdate={handleTimeUpdate}
        />
        
        {/* preview-only 자막 영역 가리기/새 자막 오버레이 */}
        {editCommand && (editCommand.cover_subtitle_area || editCommand.add_subtitle) && (
          <div className="absolute bottom-14 left-0 w-full px-4 pointer-events-none">
            <div className="mx-auto w-full max-w-[92%]">
              <span className="inline-block text-[11px] bg-red-600/90 text-white px-2 py-0.5 rounded mb-1 font-semibold">
                Preview-only UI · 기존 자막 영역 가리기
              </span>
              <div className="w-full min-h-[56px] md:min-h-[68px] bg-black/90 border border-white/20 rounded-md flex items-center justify-center px-4">
                {editCommand.add_subtitle && (
                  <p className={`text-white font-bold text-center leading-tight drop-shadow-lg ${
                    editCommand.subtitle_size === 'large' ? 'text-xl sm:text-2xl md:text-3xl' :
                    editCommand.subtitle_size === 'small' ? 'text-xs sm:text-sm md:text-base' :
                    'text-base sm:text-lg md:text-xl'
                  }`}>
                    {editCommand.subtitle_text?.trim() || DEFAULT_SUBTITLE}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 재생 중 표시 */}
      {playingLabel && (
        <p className="text-center text-lg font-semibold text-blue-600 mb-3 animate-pulse">
          🎬 지금 재생 중: {playingLabel}
        </p>
      )}

      {/* 상태별 표시 */}
      {videoState === "loading" && (
        <div className="text-center py-8">
          <div className="inline-block w-8 h-8 border-4 border-blue-300 border-t-blue-600 rounded-full animate-spin mb-3"></div>
          <p className="text-xl text-gray-500">영상을 불러오는 중입니다...</p>
        </div>
      )}

      {videoState === "error" && (
        <div className="text-center py-8 bg-red-50 rounded-xl border border-red-200">
          <p className="text-xl text-red-600 font-bold mb-2">⚠️ 영상을 불러올 수 없습니다</p>
          <p className="text-gray-500">원본 영상 파일이 서버에 없거나 형식이 지원되지 않습니다.</p>
        </div>
      )}

      {videoState === "ready" && (
        <>
          {/* ★ 썸네일 타임라인 */}
          <ThumbnailTimeline
            jobId={jobId}
            clips={clips}
            videoRef={videoRef}
            videoDuration={duration}
          />

          {clipA && clipB && (
            <p className="text-sm text-gray-600 mb-3">
              <span className="font-semibold text-blue-600">A: {clipA.source_start}~{clipA.source_end}초</span>
              {" · "}
              <span className="font-semibold text-green-600">B: {clipB.source_start}~{clipB.source_end}초</span>
            </p>
          )}

          {/* 구간 버튼 */}
          {renderSegmentButtons()}

          <div className="mt-6" />

          {/* 타임라인 비교 */}
          {renderTimeline("📼 원본 영상 순서", original)}

          <div className="flex justify-center my-2">
            <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </div>

          {renderTimeline("✨ 수정 후 적용될 순서", modified)}

          <p className="text-gray-400 text-sm mt-3 text-center">
            * 타임라인 블록이나 위의 버튼을 누르면 해당 구간이 바로 재생됩니다.
          </p>
        </>
      )}
    </div>
  );
}
