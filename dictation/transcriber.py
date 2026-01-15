"""Speech-to-text transcription using OpenAI Whisper."""

import numpy as np
import whisper
from .config import get_config, DeviceType, ModelSize
from .audio import process_audio

_model: whisper.Whisper | None = None
_current_device: DeviceType | None = None
_current_model_size: ModelSize | None = None


def cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def get_model() -> whisper.Whisper:
    global _model, _current_device, _current_model_size

    config = get_config()
    device = config.device
    model_size = config.model

    if device == "cuda" and not cuda_available():
        device = "cpu"

    if _model is None or _current_device != device or _current_model_size != model_size:
        _model = whisper.load_model(model_size, device=device)
        _current_device = device
        _current_model_size = model_size

    return _model


def reload_model() -> None:
    global _model
    _model = None
    get_model()


def is_silence(audio: np.ndarray, threshold: float) -> bool:
    """Check if audio is mostly silence based on RMS energy."""
    if len(audio) == 0:
        return True
    rms = np.sqrt(np.mean(audio**2))
    return rms < threshold


# Common Whisper hallucinations on silence/noise
HALLUCINATIONS = {
    "thank you",
    "thanks for watching",
    "thanks for listening",
    "subscribe",
    "like and subscribe",
    "see you next time",
    "bye",
    "goodbye",
    "you",
    "the end",
    "...",
    ".",
}


def is_hallucination(text: str) -> bool:
    """Check if text is a common Whisper hallucination."""
    cleaned = text.lower().strip().rstrip(".!?,")
    return cleaned in HALLUCINATIONS or len(cleaned) < 2


def transcribe(audio: np.ndarray) -> str:
    config = get_config()
    if len(audio) == 0 or is_silence(audio, config.silence_threshold):
        return ""

    # Apply audio processing
    audio = process_audio(
        audio,
        normalize=config.audio_normalize,
        compress=config.audio_compress,
        highpass=config.audio_highpass,
    )

    model = get_model()
    language = None if config.language == "auto" else config.language

    result = model.transcribe(
        audio,
        language=language,
        fp16=config.device == "cuda",
    )

    text = result["text"].strip()
    if is_hallucination(text):
        return ""
    return text
