"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import {
  getTimelineThumbnails,
  getThumbnailAbsoluteUrl,
  type TimelineThumbnail,
} from "@/lib/api";

interface Clip {
  id: string;
  source_start: number;
  source_end: number;
  new_order: number;
}

interface ThumbnailTimelineProps {
  jobId: string;
  clips: Clip[];
  /** 부모의 <video> ref — currentTime 연동용 */
  videoRef: React.RefObject<HTMLVideoElement | null>;
  /** 부모 video 엘리먼트에서 읽은 duration (API fallback용) */
  videoDuration?: number;
}

type LoadState = "loading" | "ready" | "error";

export default function ThumbnailTimeline({
  jobId,
  clips,
  videoRef,
  videoDuration = 0,
}: ThumbnailTimelineProps) {
  const [thumbs, setThumbs] = useState<TimelineThumbnail[]>([]);
  const [duration, setDuration] = useState(0);
  const [state, setState] = useState<LoadState>("loading");
  const [currentTime, setCurrentTime] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  const THUMB_WIDTH = 80;
  const THUMB_GAP = 2;
  const TRACK_PADDING = 4;

  // ── 썸네일 데이터 로드 ─────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await getTimelineThumbnails(jobId);
        if (cancelled) return;
        setThumbs(data.thumbnails);
        // API duration이 0이면 부모 video에서 받은 값 사용
        const apiDur = data.duration;
        setDuration(apiDur > 0 ? apiDur : videoDuration);
        setState(data.thumbnails.length > 0 ? "ready" : "error");
      } catch {
        if (!cancelled) {
          // API 실패해도 videoDuration 있으면 설정
          if (videoDuration > 0) setDuration(videoDuration);
          setState("error");
        }
      }
    };
    load();
    return () => { cancelled = true; };
  }, [jobId, videoDuration]);

  // ── 비디오 currentTime 추적 ──────────────────────────────────────────
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handler = () => setCurrentTime(video.currentTime);
    setCurrentTime(video.currentTime);
    video.addEventListener("timeupdate", handler);
    return () => video.removeEventListener("timeupdate", handler);
  }, [videoRef]);

  // ── 클릭 시 비디오 시간 이동 ──────────────────────────────────────────
  const seekTo = useCallback(
    (time: number) => {
      if (videoRef.current) {
        videoRef.current.currentTime = time;
        setCurrentTime(time);
        videoRef.current.play().catch(() => {});
      }
    },
    [videoRef]
  );

  // ── 구간 A/B 매핑 (단일 기준: clips[0], clips[1]) ────────────────────
  const clipA = clips[0] ?? null;
  const clipB = clips[1] ?? null;

  const getClipInfo = (time: number) => {
    if (clipA && time >= clipA.source_start && time < clipA.source_end) {
      return { label: "A", border: "border-blue-400", bg: "bg-blue-400/30", ring: "ring-blue-400" };
    }
    if (clipB && time >= clipB.source_start && time < clipB.source_end) {
      return { label: "B", border: "border-green-400", bg: "bg-green-400/30", ring: "ring-green-400" };
    }
    return null;
  };

  // ── 재생 헤드 위치 (%) ───────────────────────────────────────────────
  const safeDuration = Number.isFinite(duration) && duration > 0 ? duration : 0;
  const safeCurrentTime = Number.isFinite(currentTime) ? currentTime : 0;
  const trackStep = THUMB_WIDTH + THUMB_GAP;
  const maxSecond = Math.max(0, thumbs.length - 1);
  const clampedTime = Math.min(Math.max(0, safeCurrentTime), maxSecond);
  const headLeftPx = thumbs.length > 0 ? TRACK_PADDING + (clampedTime * trackStep) : null;

  // ── 로딩 상태 ────────────────────────────────────────────────────────
  if (state === "loading") {
    return (
      <div className="w-full bg-gray-50 rounded-xl p-4 mb-4 border border-gray-200">
        <div className="flex items-center justify-center gap-3 py-4">
          <div className="w-5 h-5 border-3 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
          <span className="text-gray-500">썸네일 타임라인 생성 중...</span>
        </div>
      </div>
    );
  }

  if (state === "error") {
    return (
      <div className="w-full bg-yellow-50 rounded-xl p-4 mb-4 border border-yellow-200 text-center">
        <p className="text-yellow-700 font-semibold">
          ⚠️ 썸네일을 생성할 수 없습니다
        </p>
        <p className="text-yellow-600 text-sm mt-1">
          영상 파일이 없거나 형식이 지원되지 않을 수 있습니다.
        </p>
      </div>
    );
  }

  // ── 메인 렌더링 ───────────────────────────────────────────────────────
  return (
    <div className="w-full mb-4">
      <h3 className="text-lg font-bold text-gray-700 mb-2 flex items-center gap-2">
        🎞️ 영상 썸네일 타임라인
        <span className="text-sm font-normal text-gray-400">
          {duration > 0 ? `(총 ${duration.toFixed(1)}초)` : "(길이 정보 없음)"}
        </span>
      </h3>

      {/* 구간 범례 */}
      {clips.length >= 2 && (
        <div className="flex gap-4 mb-2 text-sm">
          <span className="flex items-center gap-1">
            <span className="inline-block w-4 h-4 rounded bg-blue-400/50 border-2 border-blue-400" />
            구간 A ({clipA?.source_start}~{clipA?.source_end}초)
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-4 h-4 rounded bg-green-400/50 border-2 border-green-400" />
            구간 B ({clipB?.source_start}~{clipB?.source_end}초)
          </span>
        </div>
      )}

      {/* 썸네일 스크롤 영역 */}
      <div className="relative">
        {/* 썸네일 목록 */}
        <div
          ref={scrollRef}
          className="overflow-x-auto rounded-lg border-2 border-gray-300 bg-gray-900 p-1"
          style={{ scrollbarWidth: "thin" }}
        >
          <div className="relative w-max min-w-full">
            {/* 재생 헤드 (세로선) */}
            {headLeftPx !== null && (
              <div
                className="absolute top-0 bottom-0 z-20 pointer-events-none"
                style={{ left: `${headLeftPx}px` }}
              >
                <div className="w-0.5 h-full bg-red-500" />
                <div
                  className="absolute -top-1 left-1/2 -translate-x-1/2
                             w-3 h-3 bg-red-500 rounded-full border-2 border-white shadow"
                />
              </div>
            )}

            <div className="flex gap-0.5">
          {thumbs.map((thumb) => {
            const clip = getClipInfo(thumb.time);
            const isCurrent =
              safeCurrentTime >= thumb.time && safeCurrentTime < thumb.time + 1;

            return (
              <div
                key={thumb.time}
                onClick={() => seekTo(thumb.time)}
                className={`
                  relative flex-shrink-0 cursor-pointer transition-all
                  rounded overflow-hidden
                  ${clip ? `ring-2 ${clip.ring} ${clip.bg}` : ""}
                  ${isCurrent ? "ring-2 ring-red-400 scale-105" : "hover:scale-105"}
                `}
                style={{ width: 80, height: 45 }}
                title={`${thumb.time}초로 이동`}
              >
                <img
                  src={getThumbnailAbsoluteUrl(thumb.url)}
                  alt={`${thumb.time}초`}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
                {/* 시간 라벨 */}
                <span className="absolute bottom-0 right-0 bg-black/70 text-white text-[10px] px-1 rounded-tl">
                  {thumb.time}s
                </span>
                {/* 구간 라벨 */}
                {clip && (
                  <span
                    className={`absolute top-0 left-0 text-white text-[10px] font-bold px-1 rounded-br ${
                      clip.label === "A" ? "bg-blue-500" : "bg-green-500"
                    }`}
                  >
                    {clip.label}
                  </span>
                )}
              </div>
            );
          })}
            </div>
          </div>
        </div>
      </div>

      <p className="text-gray-400 text-xs mt-1 text-center">
        * 썸네일을 클릭하면 해당 시간으로 영상이 이동합니다.
      </p>
    </div>
  );
}
