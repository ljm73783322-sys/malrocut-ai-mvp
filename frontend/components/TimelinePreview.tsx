"use client";

import React, { useRef, useState, useEffect } from "react";
import { API_BASE_URL } from "@/lib/api";

interface Clip {
  id: string;
  source_start: number;
  source_end: number;
  new_order: number;
}

interface TimelinePreviewProps {
  jobId: string;
  clips: Clip[];
}

interface Segment {
  id: string;
  label: string;
  start: number;
  end: number;
  color: string;
  isModified: boolean;
}

export default function TimelinePreview({ jobId, clips }: TimelinePreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [duration, setDuration] = useState<number>(0);
  const [activeSegment, setActiveSegment] = useState<Segment | null>(null);

  // 비디오 메타데이터가 로드되면 전체 길이를 설정
  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  // 비디오 재생 중 구간 끝을 넘어가면 정지하는 간단한 로직
  const handleTimeUpdate = () => {
    if (videoRef.current && activeSegment) {
      if (videoRef.current.currentTime >= activeSegment.end) {
        videoRef.current.pause();
        setActiveSegment(null);
      }
    }
  };

  const playSegment = (seg: Segment) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seg.start;
      videoRef.current.play();
      setActiveSegment(seg);
    }
  };

  // 구간 분할 로직
  const buildSegments = () => {
    if (clips.length !== 2 || duration === 0) return { original: [], modified: [] };

    const sorted = [...clips].sort((a, b) => a.source_start - b.source_start);
    const c1 = sorted[0];
    const c2 = sorted[1];

    const s1 = c1.source_start;
    const e1 = Math.min(c1.source_end, duration);
    const s2 = c2.source_start;
    const e2 = Math.min(c2.source_end, duration);

    // 구간 배열 정의
    const original: Segment[] = [];
    const pushSeg = (arr: Segment[], start: number, end: number, label: string, color: string, isMod: boolean) => {
      if (end - start > 0.1) {
        arr.push({ id: Math.random().toString(), start, end, label, color, isModified: isMod });
      }
    };

    pushSeg(original, 0, s1, "기본 구간", "bg-gray-200", false);
    pushSeg(original, s1, e1, "구간 A", "bg-blue-300", true);
    pushSeg(original, e1, s2, "기본 구간", "bg-gray-200", false);
    pushSeg(original, s2, e2, "구간 B", "bg-green-300", true);
    pushSeg(original, e2, duration, "기본 구간", "bg-gray-200", false);

    // 수정 후 배열
    const modified: Segment[] = [];
    pushSeg(modified, 0, s1, "기본 구간", "bg-gray-200", false);
    pushSeg(modified, s2, e2, "구간 B (이동됨)", "bg-green-300", true);
    pushSeg(modified, e1, s2, "기본 구간", "bg-gray-200", false);
    pushSeg(modified, s1, e1, "구간 A (이동됨)", "bg-blue-300", true);
    pushSeg(modified, e2, duration, "기본 구간", "bg-gray-200", false);

    return { original, modified };
  };

  const { original, modified } = buildSegments();

  const renderTimeline = (title: string, segments: Segment[]) => (
    <div className="mb-6">
      <h3 className="text-xl font-bold mb-3">{title}</h3>
      <div className="flex w-full h-16 rounded-xl overflow-hidden border-2 border-gray-300 shadow-sm">
        {segments.map((seg, i) => {
          const widthPct = ((seg.end - seg.start) / duration) * 100;
          return (
            <div
              key={i}
              onClick={() => playSegment(seg)}
              className={`h-full flex items-center justify-center cursor-pointer transition-opacity hover:opacity-80 border-r border-white ${seg.color}`}
              style={{ width: `${widthPct}%` }}
              title={`${seg.start}초 ~ ${seg.end}초 재생`}
            >
              <span className="text-sm font-semibold whitespace-nowrap overflow-hidden px-1">
                {seg.label}
              </span>
            </div>
          );
        })}
      </div>
      <p className="text-gray-500 text-sm mt-2 text-center">
        * 색칠된 블록을 누르면 해당 영상 구간이 바로 재생됩니다.
      </p>
    </div>
  );

  return (
    <div className="w-full bg-white rounded-2xl shadow-lg p-6 mb-8 border-2 border-blue-100">
      <h2 className="text-2xl font-extrabold text-blue-900 mb-6 flex items-center">
        <span className="bg-blue-100 text-blue-600 px-3 py-1 rounded-lg mr-3 text-lg">기능 미리보기</span>
        컷 순서 변경 확인
      </h2>

      <div className="mb-6 bg-black rounded-xl overflow-hidden shadow-md flex justify-center">
        <video
          ref={videoRef}
          src={`${API_BASE_URL}/api/jobs/${jobId}/download/original_video`}
          controls
          className="max-h-[300px] w-auto"
          onLoadedMetadata={handleLoadedMetadata}
          onTimeUpdate={handleTimeUpdate}
        />
      </div>

      {duration > 0 ? (
        <>
          {renderTimeline("원본 영상 순서", original)}
          <div className="flex justify-center my-4">
            <svg className="w-8 h-8 text-gray-400 animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
          </div>
          {renderTimeline("수정 후 적용될 순서", modified)}
        </>
      ) : (
        <div className="text-center py-10 text-gray-500">
          영상 정보를 불러오는 중입니다...
        </div>
      )}
    </div>
  );
}
