"use client";
import type { ChangeEvent, PointerEvent } from "react";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  getDownloadUrl,
  getRepresentativeThumbnailBaseUrl,
  getRepresentativeThumbnailUrl,
  getResultPackageDownloadUrl,
  updateJobThumbnailText,
  uploadJobThumbnail,
  type ThumbnailTextPayload,
} from "@/lib/api";

const POSITION_PERCENT = {
  top: { x: 50, y: 20 },
  center: { x: 50, y: 50 },
  bottom: { x: 50, y: 80 },
} as const;

function clampPercent(value: number): number {
  return Math.min(100, Math.max(0, value));
}

function getInitialTextPosition(position: ThumbnailTextPayload["position"]) {
  return POSITION_PERCENT[position] ?? POSITION_PERCENT.center;
}

function normalizeHexColor(value: string): string {
  const trimmed = value.trim();
  const withoutHash = trimmed.startsWith("#") ? trimmed.slice(1) : trimmed;
  const expanded =
    withoutHash.length === 3
      ? withoutHash
          .split("")
          .map((char) => `${char}${char}`)
          .join("")
      : withoutHash;

  if (!/^[0-9a-fA-F]{6}$/.test(expanded)) {
    throw new Error("Invalid hex color");
  }

  return `#${expanded.toUpperCase()}`;
}

export default function ResultPage({ params }: { params: { job_id: string } }) {
  const router = useRouter();
  const [thumbnailError, setThumbnailError] = useState(false);
  const [thumbnailFile, setThumbnailFile] = useState<File | null>(null);
  const [thumbnailMessage, setThumbnailMessage] = useState<string | null>(null);
  const [thumbnailActionError, setThumbnailActionError] = useState<
    string | null
  >(null);
  const [thumbnailBusy, setThumbnailBusy] = useState(false);
  const [thumbnailVersion, setThumbnailVersion] = useState(Date.now());
  const [thumbnailTextPayload, setThumbnailTextPayload] =
    useState<ThumbnailTextPayload>({
      text: "",
      font_size: 64,
      text_color: "#FFFF00",
      background_color: "#000000",
      position: "center",
      position_x: POSITION_PERCENT.center.x,
      position_y: POSITION_PERCENT.center.y,
    });
  const thumbnailPreviewRef = useRef<HTMLDivElement>(null);

  const videoUrl = getDownloadUrl(params.job_id, "video");
  const baseThumbnailUrl = getRepresentativeThumbnailUrl(params.job_id);
  const baseThumbnailEditUrl = getRepresentativeThumbnailBaseUrl(params.job_id);
  const thumbnailUrl = `${baseThumbnailUrl}?v=${thumbnailVersion}`;
  const thumbnailEditBackgroundUrl = `${baseThumbnailEditUrl}?v=${thumbnailVersion}`;
  const thumbnailDownloadUrl = getDownloadUrl(params.job_id, "thumbnail");
  const packageDownloadUrl = getResultPackageDownloadUrl(params.job_id);
  const initialTextPosition = getInitialTextPosition(
    thumbnailTextPayload.position,
  );
  const overlayPositionX = clampPercent(
    thumbnailTextPayload.position_x ?? initialTextPosition.x,
  );
  const overlayPositionY = clampPercent(
    thumbnailTextPayload.position_y ?? initialTextPosition.y,
  );
  const hasThumbnailText = thumbnailTextPayload.text.trim().length > 0;
  const previewThumbnailUrl = hasThumbnailText
    ? thumbnailEditBackgroundUrl
    : thumbnailUrl;

  const refreshThumbnail = () => {
    setThumbnailError(false);
    setThumbnailVersion(Date.now());
  };

  const handleThumbnailFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setThumbnailFile(event.target.files?.[0] ?? null);
  };

  const updateTextPositionFromPointer = (event: PointerEvent<HTMLElement>) => {
    const preview = thumbnailPreviewRef.current;
    if (!preview) {
      return;
    }

    const rect = preview.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) {
      return;
    }

    const nextX = clampPercent(
      ((event.clientX - rect.left) / rect.width) * 100,
    );
    const nextY = clampPercent(
      ((event.clientY - rect.top) / rect.height) * 100,
    );
    setThumbnailTextPayload((prev) => ({
      ...prev,
      position_x: Number(nextX.toFixed(2)),
      position_y: Number(nextY.toFixed(2)),
    }));
  };

  const handleTextPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    updateTextPositionFromPointer(event);
  };

  const handleTextPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!event.currentTarget.hasPointerCapture(event.pointerId)) {
      return;
    }

    updateTextPositionFromPointer(event);
  };

  const handleTextPointerUp = (event: PointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const handleUploadThumbnail = async () => {
    if (!thumbnailFile) {
      setThumbnailActionError("업로드할 썸네일 이미지를 선택해 주세요.");
      setThumbnailMessage(null);
      return;
    }

    setThumbnailBusy(true);
    setThumbnailActionError(null);
    setThumbnailMessage(null);

    try {
      await uploadJobThumbnail(params.job_id, thumbnailFile);
      setThumbnailMessage("직접 업로드한 썸네일이 적용되었습니다.");
      refreshThumbnail();
    } catch (err) {
      console.error("[result] 썸네일 업로드 실패:", err);
      setThumbnailActionError(
        "썸네일 업로드에 실패했습니다. png, jpg, jpeg, webp 이미지를 사용해 주세요.",
      );
    } finally {
      setThumbnailBusy(false);
    }
  };

  const handleApplyThumbnailText = async () => {
    if (!thumbnailTextPayload.text.trim()) {
      setThumbnailActionError("썸네일 문구를 입력해 주세요.");
      setThumbnailMessage(null);
      return;
    }

    setThumbnailBusy(true);
    setThumbnailActionError(null);
    setThumbnailMessage(null);

    try {
      const latestPayload: ThumbnailTextPayload = {
        text: thumbnailTextPayload.text,
        font_size: thumbnailTextPayload.font_size,
        text_color: normalizeHexColor(thumbnailTextPayload.text_color),
        background_color: normalizeHexColor(
          thumbnailTextPayload.background_color,
        ),
        position: thumbnailTextPayload.position,
        position_x: overlayPositionX,
        position_y: overlayPositionY,
      };

      if (process.env.NODE_ENV !== "production") {
        console.debug("[result] thumbnail text payload", latestPayload);
      }

      await updateJobThumbnailText(params.job_id, latestPayload);
      setThumbnailMessage("썸네일 문구가 적용되었습니다.");
      refreshThumbnail();
    } catch (err) {
      console.error("[result] 썸네일 문구 적용 실패:", err);
      setThumbnailActionError(
        "썸네일 문구 적용에 실패했습니다. 입력값을 확인해 주세요.",
      );
    } finally {
      setThumbnailBusy(false);
    }
  };

  return (
    <div className="flex flex-col items-center space-y-12 py-10 w-full max-w-5xl mx-auto px-4">
      <h2 className="text-5xl font-bold text-green-600 text-center">
        🎉 짜잔! 완벽하게 편집되었습니다.
      </h2>

      <section className="w-full bg-white rounded-2xl shadow-lg border-2 border-blue-100 p-6">
        <h3 className="text-2xl font-extrabold text-blue-900 mb-4">
          📹 완성 영상 미리보기
        </h3>
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
          <h3 className="text-2xl font-extrabold text-orange-700">
            🎬 유튜브 대표 썸네일
          </h3>
          <p className="text-lg text-gray-600">
            렌더링된 영상에서 자동 생성된 대표 썸네일입니다. 위 썸네일의 문구
            박스를 드래그해서 위치를 조정할 수 있습니다.
          </p>
        </div>

        {!thumbnailError ? (
          <div
            ref={thumbnailPreviewRef}
            className="relative mx-auto w-full max-w-3xl overflow-hidden rounded-2xl border-2 border-orange-100 bg-gray-100 shadow-lg"
          >
            <img
              src={previewThumbnailUrl}
              alt="유튜브 대표 썸네일 미리보기"
              className="block w-full object-cover"
              onError={() => setThumbnailError(true)}
            />
            {hasThumbnailText && (
              <div
                role="button"
                tabIndex={0}
                aria-label="썸네일 문구 위치 드래그"
                onPointerDown={handleTextPointerDown}
                onPointerMove={handleTextPointerMove}
                onPointerUp={handleTextPointerUp}
                onPointerCancel={handleTextPointerUp}
                className="absolute z-20 max-w-[90%] cursor-move select-none touch-none whitespace-pre-wrap rounded-lg px-4 py-2 text-center font-extrabold leading-tight shadow-lg ring-2 ring-white/70 pointer-events-auto"
                style={{
                  left: `${overlayPositionX}%`,
                  top: `${overlayPositionY}%`,
                  transform: "translate(-50%, -50%)",
                  color: thumbnailTextPayload.text_color,
                  backgroundColor: thumbnailTextPayload.background_color,
                  fontSize: `${thumbnailTextPayload.font_size}px`,
                }}
              >
                {thumbnailTextPayload.text}
              </div>
            )}
          </div>
        ) : (
          <div className="w-full max-w-3xl mx-auto rounded-2xl border-2 border-dashed border-gray-300 bg-gray-50 p-12 text-center text-xl text-gray-500">
            썸네일을 아직 불러올 수 없습니다.
          </div>
        )}

        <div className="mt-6 rounded-2xl border-2 border-orange-100 bg-orange-50 p-5">
          <h4 className="text-2xl font-extrabold text-orange-800 mb-4">
            썸네일 편집
          </h4>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-xl bg-white p-4 shadow-sm border border-orange-100">
              <label className="block text-lg font-bold text-gray-800 mb-2">
                직접 썸네일 이미지
              </label>
              <input
                type="file"
                accept="image/png,image/jpeg,image/jpg,image/webp"
                onChange={handleThumbnailFileChange}
                className="block w-full text-sm text-gray-700 file:mr-4 file:rounded-lg file:border-0 file:bg-orange-100 file:px-4 file:py-2 file:font-bold file:text-orange-700 hover:file:bg-orange-200"
              />
              <button
                type="button"
                onClick={handleUploadThumbnail}
                disabled={thumbnailBusy}
                className="mt-4 w-full rounded-xl bg-orange-500 px-5 py-3 text-lg font-bold text-white shadow hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-300"
              >
                직접 썸네일 업로드
              </button>
            </div>

            <div className="rounded-xl bg-white p-4 shadow-sm border border-orange-100">
              <label className="block text-lg font-bold text-gray-800 mb-2">
                썸네일 문구
              </label>
              <p className="mb-3 text-sm font-medium text-gray-500">
                문구를 다시 적용하면 이전 문구는 사라지고 새 문구만 적용됩니다.
              </p>
              <input
                type="text"
                value={thumbnailTextPayload.text}
                onChange={(event) =>
                  setThumbnailTextPayload((prev) => ({
                    ...prev,
                    text: event.target.value,
                  }))
                }
                placeholder="썸네일 문구"
                className="w-full rounded-lg border border-gray-300 px-4 py-3 text-lg"
              />

              <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="text-sm font-bold text-gray-700">
                  글자 크기
                  <input
                    type="number"
                    min={12}
                    max={180}
                    value={thumbnailTextPayload.font_size}
                    onChange={(event) =>
                      setThumbnailTextPayload((prev) => ({
                        ...prev,
                        font_size: Number(event.target.value),
                      }))
                    }
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
                  />
                </label>
                <label className="text-sm font-bold text-gray-700">
                  위치
                  <select
                    value={thumbnailTextPayload.position}
                    onChange={(event) => {
                      const position = event.target
                        .value as ThumbnailTextPayload["position"];
                      const nextPosition = getInitialTextPosition(position);
                      setThumbnailTextPayload((prev) => ({
                        ...prev,
                        position,
                        position_x: nextPosition.x,
                        position_y: nextPosition.y,
                      }));
                    }}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
                  >
                    <option value="top">위</option>
                    <option value="center">가운데</option>
                    <option value="bottom">아래</option>
                  </select>
                </label>
                <label className="text-sm font-bold text-gray-700">
                  글자 색상
                  <input
                    type="color"
                    value={thumbnailTextPayload.text_color}
                    onChange={(event) =>
                      setThumbnailTextPayload((prev) => ({
                        ...prev,
                        text_color: event.target.value,
                      }))
                    }
                    className="mt-1 h-11 w-full rounded-lg border border-gray-300 px-2 py-1"
                  />
                </label>
                <label className="text-sm font-bold text-gray-700">
                  배경 색상
                  <input
                    type="color"
                    value={thumbnailTextPayload.background_color}
                    onChange={(event) =>
                      setThumbnailTextPayload((prev) => ({
                        ...prev,
                        background_color: event.target.value,
                      }))
                    }
                    className="mt-1 h-11 w-full rounded-lg border border-gray-300 px-2 py-1"
                  />
                </label>
              </div>

              <button
                type="button"
                onClick={handleApplyThumbnailText}
                disabled={thumbnailBusy}
                className="mt-4 w-full rounded-xl bg-orange-700 px-5 py-3 text-lg font-bold text-white shadow hover:bg-orange-800 disabled:cursor-not-allowed disabled:bg-orange-300"
              >
                썸네일 문구 적용
              </button>
            </div>
          </div>

          <p className="mt-4 text-sm text-gray-500">
            위 썸네일의 문구 박스를 드래그해서 위치를 조정하세요.
          </p>
          {thumbnailMessage && (
            <p className="mt-3 rounded-lg bg-green-100 px-4 py-3 font-bold text-green-700">
              {thumbnailMessage}
            </p>
          )}
          {thumbnailActionError && (
            <p className="mt-3 rounded-lg bg-red-100 px-4 py-3 font-bold text-red-700">
              {thumbnailActionError}
            </p>
          )}
        </div>

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
          download={`malrocut-result-${params.job_id}.zip`}
          role="button"
          aria-label="전체 패키지 ZIP 다운로드"
          className="bg-purple-600 text-white text-3xl font-bold py-6 px-8 rounded-2xl shadow-lg hover:bg-purple-700 text-center"
        >
          📦 전체 패키지 ZIP 다운로드
        </a>
        <a
          href={getDownloadUrl(params.job_id, "subtitle")}
          className="bg-gray-600 text-white text-3xl font-bold py-6 px-8 rounded-2xl shadow-lg hover:bg-gray-700 text-center"
        >
          📝 자막 파일 저장하기
        </a>
      </div>

      <button
        onClick={() => router.push("/")}
        className="mt-8 text-2xl text-blue-500 underline"
      >
        처음으로 돌아가기
      </button>
    </div>
  );
}
