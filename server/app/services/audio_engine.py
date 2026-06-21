"""
server/app/services/audio_engine.py

Thai TTS audio engine using Microsoft Edge TTS (th-TH-PremwadeeNeural).
Converts voiceover_script segments from a lesson episode JSON into a single
merged audio file that is time-aligned with the Manim video.

Usage:
    engine = AudioEngine(output_dir="renders/audio")
    result = await engine.generate_episode_audio(episode_data)
    # result["audio_path"] → path to the merged .mp3

Dependencies (add to requirements.txt):
    edge-tts>=6.1.9
    pydub>=0.25.1
    ffmpeg  (system binary — must be installed)
"""

import asyncio
import os
import math
import logging
import tempfile
from pathlib import Path

import edge_tts
from pydub import AudioSegment
from pydub.generators import Sine

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Voice configuration
# ─────────────────────────────────────────────────────────────────────────────
THAI_VOICE = "th-TH-PremwadeeNeural"   # Female, clear, academic tone
THAI_VOICE_MALE = "th-TH-NiwatNeural"  # Male alternative

# Edge TTS SSML rate/pitch tuning for physics explanation style
# Slightly slower than default for comprehension, natural pitch
TTS_RATE = "+0%"     # normal speed — voiceover_script already targets ~12 chars/sec
TTS_PITCH = "+0Hz"   # natural pitch
TTS_VOLUME = "+0%"   # normal volume

FRAME_RATE = 60      # must match Manim config.frame_rate


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ms(seconds: float) -> int:
    """Convert seconds → milliseconds (int) for pydub."""
    return int(round(seconds * 1000))


def _silence(duration_ms: int) -> AudioSegment:
    """Return a silent AudioSegment of the given duration."""
    return AudioSegment.silent(duration=max(0, duration_ms))


async def _synthesize_segment(
    text: str,
    output_path: str,
    voice: str = THAI_VOICE,
    rate: str = TTS_RATE,
    pitch: str = TTS_PITCH,
    volume: str = TTS_VOLUME,
) -> bool:
    """
    Synthesize one text segment to an MP3 file using edge-tts.
    Returns True on success, False on failure.
    """
    try:
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )
        await communicate.save(output_path)
        return True
    except Exception as exc:
        logger.error(f"TTS synthesis failed for text '{text[:60]}…': {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Main engine
# ─────────────────────────────────────────────────────────────────────────────

class AudioEngine:
    def __init__(
        self,
        output_dir: str = "renders/audio",
        voice: str = THAI_VOICE,
    ):
        self.output_dir = output_dir
        self.voice = voice
        os.makedirs(output_dir, exist_ok=True)

    # ─────────────────────────────────────────────────────────────────────────
    async def generate_episode_audio(
        self,
        episode_data: dict,
        fade_ms: int = 50,
    ) -> dict:
        """
        Generate a single time-aligned audio file for one episode.

        The function:
          1. Reads voiceover_script segments from episode_data.
          2. Synthesises each segment's thai_text to a temp MP3 via edge-tts.
          3. Trims or pads each clip to fit exactly (end_time - start_time) seconds.
          4. Assembles all clips into one master track with silence gaps, so that
             clip N starts at exactly segment["start_time_seconds"] in the output.
          5. Exports the master track to {output_dir}/audio_ep_{ep_num}.mp3.

        Args:
            episode_data: One episode dict from the Gemini lesson JSON.
            fade_ms:      Short crossfade (ms) applied between clips.

        Returns:
            {
                "status": "success" | "error",
                "audio_path": str,           # absolute path to merged MP3
                "episode_number": int,
                "total_duration_seconds": float,
                "segments_synthesised": int,
                "segments_failed": int,
            }
        """
        ep_num = episode_data.get("episode_number", 0)
        voiceover = episode_data.get("voiceover_script", [])

        if not voiceover:
            logger.warning(f"Episode {ep_num} has no voiceover_script — skipping audio.")
            return {
                "status": "error",
                "message": "No voiceover_script in episode data.",
                "episode_number": ep_num,
            }

        # Sort segments by start time (defensive — should already be sorted)
        segments = sorted(voiceover, key=lambda s: s.get("start_time_seconds", 0))

        # Total track length = end_time of last segment
        total_duration_s = segments[-1].get("end_time_seconds", 30.0)
        total_duration_s = max(total_duration_s, 30.0)  # minimum 30 seconds

        # Build master timeline (start with silence)
        master = _silence(_ms(total_duration_s))

        synthesised = 0
        failed = 0

        with tempfile.TemporaryDirectory() as tmp_dir:
            # Synthesise all segments concurrently
            tasks = []
            temp_paths = []
            for i, seg in enumerate(segments):
                tmp_path = os.path.join(tmp_dir, f"seg_{i:03d}.mp3")
                temp_paths.append(tmp_path)
                text = seg.get("thai_text", "").strip()
                if not text:
                    temp_paths[-1] = None   # will be treated as silence
                    continue
                tasks.append(
                    _synthesize_segment(text, tmp_path, voice=self.voice)
                )

            # Run all TTS calls in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Map results back (accounting for skipped empty segments)
            result_iter = iter(results)
            for i, seg in enumerate(segments):
                start_ms = _ms(seg.get("start_time_seconds", 0))
                end_ms = _ms(seg.get("end_time_seconds", start_ms / 1000 + 5))
                slot_ms = end_ms - start_ms

                tmp_path = temp_paths[i]
                if tmp_path is None:
                    # Empty text — fill slot with silence
                    continue

                ok = next(result_iter, False)
                if isinstance(ok, Exception) or not ok:
                    logger.warning(f"Segment {i} TTS failed — filling with silence.")
                    failed += 1
                    continue

                if not os.path.exists(tmp_path):
                    logger.warning(f"Segment {i} MP3 missing — filling with silence.")
                    failed += 1
                    continue

                try:
                    clip = AudioSegment.from_mp3(tmp_path)
                except Exception as exc:
                    logger.error(f"Cannot load segment {i} MP3: {exc}")
                    failed += 1
                    continue

                # ── Fit clip to time slot ──────────────────────────────────
                clip_ms = len(clip)

                if clip_ms > slot_ms:
                    # Clip is longer than slot → speed it up slightly
                    # pydub doesn't have a built-in speed change, so we use
                    # frame_rate manipulation (changes pitch slightly — acceptable
                    # for TTS; use librosa for pitch-preserving if needed)
                    speed_ratio = clip_ms / slot_ms
                    if speed_ratio <= 1.5:   # only if adjustment is small
                        new_frame_rate = int(clip.frame_rate * speed_ratio)
                        clip = clip._spawn(
                            clip.raw_data,
                            overrides={"frame_rate": new_frame_rate},
                        ).set_frame_rate(clip.frame_rate)
                    else:
                        # Too much stretch needed — truncate and warn
                        logger.warning(
                            f"Segment {i} audio ({clip_ms}ms) much longer than slot "
                            f"({slot_ms}ms). Truncating."
                        )
                        clip = clip[:slot_ms]
                elif clip_ms < slot_ms:
                    # Clip is shorter than slot → pad with trailing silence
                    clip = clip + _silence(slot_ms - clip_ms)

                # Apply short fade in/out to avoid clicks
                if len(clip) > fade_ms * 2:
                    clip = clip.fade_in(fade_ms).fade_out(fade_ms)

                # Overlay clip onto master at the correct position
                master = master.overlay(clip, position=start_ms)
                synthesised += 1

        # ── Export ────────────────────────────────────────────────────────────
        out_filename = f"audio_ep_{ep_num}.mp3"
        out_path = os.path.join(self.output_dir, out_filename)
        try:
            master.export(out_path, format="mp3", bitrate="128k")
            logger.info(
                f"Episode {ep_num} audio exported → {out_path} "
                f"({total_duration_s:.1f}s, {synthesised} segments, {failed} failed)"
            )
            return {
                "status": "success",
                "audio_path": os.path.abspath(out_path),
                "episode_number": ep_num,
                "total_duration_seconds": total_duration_s,
                "segments_synthesised": synthesised,
                "segments_failed": failed,
            }
        except Exception as exc:
            logger.error(f"Episode {ep_num} audio export failed: {exc}")
            return {
                "status": "error",
                "message": str(exc),
                "episode_number": ep_num,
            }

    # ─────────────────────────────────────────────────────────────────────────
    async def generate_all_episodes(self, lesson_json: dict) -> list[dict]:
        """Generate audio for every episode in a lesson JSON. Returns list of results."""
        tasks = [
            self.generate_episode_audio(ep)
            for ep in lesson_json.get("episodes", [])
        ]
        return await asyncio.gather(*tasks)

    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def list_thai_voices() -> list[str]:
        """Convenience: return all available Thai voices from edge-tts."""
        return [THAI_VOICE, THAI_VOICE_MALE]

    @staticmethod
    async def preview_voice(
        text: str = "สวัสดีครับ นี่คือเสียงทดสอบจาก pageSpark",
        voice: str = THAI_VOICE,
        output_path: str = "preview_voice.mp3",
    ) -> str:
        """Quick preview of a voice. Returns path to the generated MP3."""
        ok = await _synthesize_segment(text, output_path, voice=voice)
        if ok:
            return output_path
        raise RuntimeError(f"Preview synthesis failed for voice '{voice}'.")