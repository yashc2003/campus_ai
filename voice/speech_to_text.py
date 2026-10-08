from __future__ import annotations

import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path


def _ensure_ffmpeg() -> str | None:
    if shutil.which("ffmpeg"):
        return None
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError("FFmpeg is missing. Install the voice extras with `python -m pip install -r requirements-voice.txt`.") from exc


@lru_cache(maxsize=2)
def _load_model(model_name: str):
    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError("Whisper is not installed. Run `python -m pip install -r requirements-voice.txt` in the app's Python environment.") from exc
    ffmpeg_path = _ensure_ffmpeg()
    if ffmpeg_path:
        import whisper.audio as whisper_audio

        def load_audio_with_bundled_ffmpeg(file: str, sr: int = whisper_audio.SAMPLE_RATE):
            command = [ffmpeg_path, "-nostdin", "-threads", "0", "-i", file,
                       "-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le", "-ar", str(sr), "-"]
            try:
                output = subprocess.run(command, capture_output=True, check=True).stdout
            except subprocess.CalledProcessError as exc:
                details = exc.stderr.decode(errors="replace") if exc.stderr else "unknown audio decoding error"
                raise RuntimeError(f"FFmpeg could not decode the audio: {details[-800:]}") from exc
            return whisper_audio.np.frombuffer(output, whisper_audio.np.int16).flatten().astype(whisper_audio.np.float32) / 32768.0

        whisper_audio.load_audio = load_audio_with_bundled_ffmpeg
    try:
        return whisper.load_model(model_name)
    except Exception as exc:
        raise RuntimeError(
            f"Whisper's '{model_name}' model could not load ({exc.__class__.__name__}). "
            "The first use downloads model weights; check internet access and try again."
        ) from exc


def transcribe_audio(audio: bytes, language: str = "auto", model_name: str = "base") -> tuple[str, str | None]:
    """Transcribe locally with Whisper. No audio leaves the machine."""
    if not audio:
        raise ValueError("Record or upload an audio clip first.")
    if model_name not in {"tiny", "base", "small"}:
        raise ValueError("Choose a supported Whisper model: tiny, base, or small.")
    model = _load_model(model_name)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        handle.write(audio)
        path = Path(handle.name)
    try:
        result = model.transcribe(str(path), language=None if language == "auto" else language)
        return result.get("text", "").strip(), result.get("language")
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg could not be started. Install the voice extras and restart the app.") from exc
    finally:
        path.unlink(missing_ok=True)
