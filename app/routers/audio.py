import gc
import os
import logging
import tempfile

import torch
import whisperx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from whisperx.audio import SAMPLE_RATE
from whisperx.diarize import DiarizationPipeline

from app.config import settings


router = APIRouter(
    prefix="/v1/audio",
    tags=["audio"],
)

logger = logging.getLogger(__name__)


def clear_cuda():
    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def get_vad_chunks(
    model,
    audio,
) -> list[dict]:
    vad_model = model.vad_model
    vad_params = model._vad_params

    waveform = vad_model.preprocess_audio(audio)

    vad_segments = vad_model({
        "waveform": waveform,
        "sample_rate": SAMPLE_RATE,
    })

    return vad_model.merge_chunks(
        vad_segments,
        vad_params["chunk_size"],
        onset=vad_params["vad_onset"],
        offset=vad_params["vad_offset"],
    )


def offset_segments(
    segments: list[dict],
    offset: float,
    language: str,
) -> list[dict]:
    result = []

    for source_segment in segments:
        segment = dict(source_segment)

        segment["language"] = language

        if segment.get("start") is not None:
            segment["start"] += offset

        if segment.get("end") is not None:
            segment["end"] += offset

        if "words" in segment:
            words = []

            for source_word in segment["words"]:
                word = dict(source_word)

                if word.get("start") is not None:
                    word["start"] += offset

                if word.get("end") is not None:
                    word["end"] += offset

                words.append(word)

            segment["words"] = words

        result.append(segment)

    return result


def normalize_result(
    segments: list[dict],
    languages: list[str],
    duration: float,
    diarization: dict,
) -> dict:
    speaker_ids = set()
    normalized_segments = []

    for index, segment in enumerate(segments, start=1):
        speaker = segment.get("speaker")

        if speaker:
            speaker_ids.add(speaker)

        words = []

        for word in segment.get("words", []):
            word_speaker = word.get("speaker")

            if word_speaker:
                speaker_ids.add(word_speaker)

            words.append({
                "word": word.get("word", "").strip(),
                "start": word.get("start"),
                "end": word.get("end"),
                "score": word.get("score"),
                "speaker": word_speaker,
            })

        normalized_segments.append({
            "id": f"seg_{index:06d}",
            "start": segment.get("start"),
            "end": segment.get("end"),
            "language": segment.get("language"),
            "speaker": speaker,
            "text": segment.get("text", "").strip(),
            "avg_logprob": segment.get("avg_logprob"),
            "words": words,
        })

    speakers = [
        {"id": speaker_id}
        for speaker_id in sorted(speaker_ids)
    ]

    return {
        "language": languages,
        "duration": round(duration, 3),
        "diarization": diarization,
        "speakers": speakers,
        "segments": normalized_segments,
    }


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    min_speakers: int | None = Form(None),
    max_speakers: int | None = Form(None),
    multilingual: bool = Form(False),
):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    suffix = os.path.splitext(file.filename or "")[1]

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix) as temp:
            while chunk := await file.read(1024 * 1024):
                temp.write(chunk)

            temp.flush()

            audio = whisperx.load_audio(temp.name)
            duration = len(audio) / SAMPLE_RATE

            # Распознавание речи
            model = whisperx.load_model(
                "large-v3",
                device,
                compute_type=compute_type,
            )

            try:
                if multilingual:
                    chunks = []
                    languages = []

                    # Используем VAD WhisperX, чтобы не резать речь по жёстким временным границам
                    vad_chunks = get_vad_chunks(
                        model,
                        audio,
                    )

                    for vad_chunk in vad_chunks:
                        offset = float(vad_chunk["start"])
                        end = float(vad_chunk["end"])

                        start_sample = int(offset * SAMPLE_RATE)
                        end_sample = int(end * SAMPLE_RATE)

                        chunk_audio = audio[
                            start_sample:end_sample
                        ]

                        if len(chunk_audio) == 0:
                            continue

                        # В multilingual-режиме язык определяется отдельно для каждого VAD-aware блока
                        language = model.detect_language(
                            chunk_audio
                        )

                        transcription = model.transcribe(
                            chunk_audio,
                            batch_size=16,
                            language=language,
                        )

                        if not transcription["segments"]:
                            continue

                        if language not in languages:
                            languages.append(language)

                        chunks.append({
                            "audio": chunk_audio,
                            "offset": offset,
                            "language": language,
                            "segments": transcription["segments"],
                        })

                else:
                    transcription = model.transcribe(
                        audio,
                        batch_size=16,
                    )

                    language = transcription["language"]
                    languages = [language]

            finally:
                del model
                clear_cuda()

            # Точное выравнивание слов по времени
            if multilingual:
                aligned_segments = []

                for language in languages:
                    align_model, metadata = (
                        whisperx.load_align_model(
                            language_code=language,
                            device=device,
                        )
                    )

                    try:
                        for chunk in chunks:
                            if chunk["language"] != language:
                                continue

                            aligned = whisperx.align(
                                chunk["segments"],
                                align_model,
                                metadata,
                                chunk["audio"],
                                device,
                                return_char_alignments=False,
                            )

                            aligned_segments.extend(
                                offset_segments(
                                    aligned["segments"],
                                    chunk["offset"],
                                    language,
                                )
                            )

                    finally:
                        del align_model
                        clear_cuda()

                aligned_segments.sort(
                    key=lambda segment: (
                        segment.get("start") or 0
                    )
                )

            else:
                align_model, metadata = whisperx.load_align_model(
                    language_code=language,
                    device=device,
                )

                try:
                    aligned = whisperx.align(
                        transcription["segments"],
                        align_model,
                        metadata,
                        audio,
                        device,
                        return_char_alignments=False,
                    )

                    aligned_segments = offset_segments(
                        aligned["segments"],
                        0,
                        language,
                    )

                finally:
                    del align_model
                    clear_cuda()

            result = {
                "segments": aligned_segments,
            }

            diarization = {
                "available": False,
                "error": None,
            }

            # Определение спикеров (доступно только с HF_TOKEN)
            if settings.hf_token:
                diarize_model = None

                try:
                    diarize_model = DiarizationPipeline(
                        token=settings.hf_token,
                        device=device,
                    )

                    diarize_segments = diarize_model(
                        audio,
                        min_speakers=min_speakers,
                        max_speakers=max_speakers,
                    )

                    result = whisperx.assign_word_speakers(
                        diarize_segments,
                        result,
                    )

                    diarization["available"] = True

                except Exception as exc:
                    diarization["error"] = str(exc)

                    logger.exception(
                        "Speaker diarization failed"
                    )

                finally:
                    if diarize_model is not None:
                        del diarize_model

                    clear_cuda()

            else:
                diarization["error"] = (
                    "HF_TOKEN is not configured"
                )

            return normalize_result(
                segments=result["segments"],
                languages=languages,
                duration=duration,
                diarization=diarization,
            )

    except Exception as exc:
        clear_cuda()

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
