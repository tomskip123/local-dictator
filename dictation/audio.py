"""Audio capture using sounddevice."""

import numpy as np
import sounddevice as sd
from threading import Lock
from typing import Callable

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = np.float32


def normalize_audio(audio: np.ndarray, target_level: float = 0.9) -> np.ndarray:
    """Normalize audio to target peak level."""
    if len(audio) == 0:
        return audio
    peak = np.max(np.abs(audio))
    if peak > 0:
        return audio * (target_level / peak)
    return audio


def compress_audio(
    audio: np.ndarray,
    threshold: float = 0.3,
    ratio: float = 4.0,
    attack_ms: float = 5.0,
    release_ms: float = 50.0,
) -> np.ndarray:
    """Apply dynamic range compression to audio."""
    if len(audio) == 0:
        return audio

    attack_samples = int(SAMPLE_RATE * attack_ms / 1000)
    release_samples = int(SAMPLE_RATE * release_ms / 1000)

    output = np.zeros_like(audio)
    envelope = 0.0

    for i, sample in enumerate(audio):
        abs_sample = abs(sample)

        # Envelope follower
        if abs_sample > envelope:
            coef = 1.0 - np.exp(-1.0 / attack_samples) if attack_samples > 0 else 1.0
        else:
            coef = 1.0 - np.exp(-1.0 / release_samples) if release_samples > 0 else 1.0
        envelope = envelope + coef * (abs_sample - envelope)

        # Apply compression
        if envelope > threshold:
            gain = threshold + (envelope - threshold) / ratio
            gain = gain / envelope if envelope > 0 else 1.0
        else:
            gain = 1.0

        output[i] = sample * gain

    return output


def apply_highpass(audio: np.ndarray, cutoff_hz: float = 80.0) -> np.ndarray:
    """Simple single-pole highpass filter to remove low rumble."""
    if len(audio) == 0:
        return audio

    rc = 1.0 / (2.0 * np.pi * cutoff_hz)
    dt = 1.0 / SAMPLE_RATE
    alpha = rc / (rc + dt)

    output = np.zeros_like(audio)
    prev_input = 0.0
    prev_output = 0.0

    for i, sample in enumerate(audio):
        output[i] = alpha * (prev_output + sample - prev_input)
        prev_input = sample
        prev_output = output[i]

    return output


def process_audio(audio: np.ndarray, normalize: bool = True, compress: bool = True, highpass: bool = True) -> np.ndarray:
    """Apply audio processing chain."""
    if len(audio) == 0:
        return audio

    if highpass:
        audio = apply_highpass(audio)
    if compress:
        audio = compress_audio(audio)
    if normalize:
        audio = normalize_audio(audio)

    return audio


class AudioRecorder:
    def __init__(self):
        self._buffer: list[np.ndarray] = []
        self._lock = Lock()
        self._stream: sd.InputStream | None = None
        self._recording = False
        self._chunk_callback: Callable[[np.ndarray], None] | None = None
        self._chunk_samples = 0
        self._samples_since_chunk = 0

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            print(f"Audio status: {status}")
        with self._lock:
            if self._recording:
                self._buffer.append(indata.copy())

                if self._chunk_callback and self._chunk_samples > 0:
                    self._samples_since_chunk += frames
                    if self._samples_since_chunk >= self._chunk_samples:
                        audio = np.concatenate(self._buffer, axis=0).flatten()
                        self._samples_since_chunk = 0
                        self._chunk_callback(audio)

    def start(self, chunk_callback: Callable[[np.ndarray], None] | None = None, chunk_seconds: float = 0) -> None:
        with self._lock:
            self._buffer.clear()
            self._recording = True
            self._chunk_callback = chunk_callback
            self._chunk_samples = int(chunk_seconds * SAMPLE_RATE) if chunk_seconds > 0 else 0
            self._samples_since_chunk = 0

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        with self._lock:
            self._recording = False
            self._chunk_callback = None

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        with self._lock:
            if not self._buffer:
                return np.array([], dtype=DTYPE)
            audio = np.concatenate(self._buffer, axis=0).flatten()
            self._buffer.clear()
            return audio

    def get_audio_so_far(self) -> np.ndarray:
        with self._lock:
            if not self._buffer:
                return np.array([], dtype=DTYPE)
            return np.concatenate(self._buffer, axis=0).flatten()

    @property
    def is_recording(self) -> bool:
        return self._recording


_recorder: AudioRecorder | None = None


def get_recorder() -> AudioRecorder:
    global _recorder
    if _recorder is None:
        _recorder = AudioRecorder()
    return _recorder
