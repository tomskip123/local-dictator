"""Audio capture using sounddevice."""

import numpy as np
import sounddevice as sd
from scipy import signal
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
        return (audio * (target_level / peak)).astype(DTYPE)
    return audio


def compress_audio(
    audio: np.ndarray,
    threshold: float = 0.3,
    ratio: float = 4.0,
    attack_ms: float = 5.0,
    release_ms: float = 50.0,
) -> np.ndarray:
    """Apply dynamic range compression to audio (vectorized)."""
    if len(audio) == 0:
        return audio

    attack_coef = 1.0 - np.exp(-1000.0 / (SAMPLE_RATE * attack_ms)) if attack_ms > 0 else 1.0
    release_coef = 1.0 - np.exp(-1000.0 / (SAMPLE_RATE * release_ms)) if release_ms > 0 else 1.0

    # Envelope follower using leaky integrator (approximate attack/release)
    abs_audio = np.abs(audio)
    avg_coef = (attack_coef + release_coef) / 2
    b = [avg_coef]
    a = [1.0, -(1.0 - avg_coef)]
    envelope = signal.lfilter(b, a, abs_audio)
    envelope = np.maximum(envelope, 1e-10)

    # Vectorized gain calculation
    gain = np.where(
        envelope > threshold,
        (threshold + (envelope - threshold) / ratio) / envelope,
        1.0
    )

    return (audio * gain).astype(DTYPE)


def apply_highpass(audio: np.ndarray, cutoff_hz: float = 80.0) -> np.ndarray:
    """Single-pole highpass filter to remove low rumble (vectorized)."""
    if len(audio) == 0:
        return audio

    rc = 1.0 / (2.0 * np.pi * cutoff_hz)
    dt = 1.0 / SAMPLE_RATE
    alpha = rc / (rc + dt)

    # IIR filter: y[n] = alpha * (y[n-1] + x[n] - x[n-1])
    b = [alpha, -alpha]
    a = [1.0, -alpha]
    return signal.lfilter(b, a, audio).astype(DTYPE)


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
    # Pre-allocate buffer for up to 5 minutes of audio
    MAX_DURATION = 300
    BUFFER_SIZE = SAMPLE_RATE * MAX_DURATION

    def __init__(self):
        self._buffer = np.zeros(self.BUFFER_SIZE, dtype=DTYPE)
        self._write_pos = 0
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
                data = indata.flatten()
                end_pos = min(self._write_pos + len(data), self.BUFFER_SIZE)
                copy_len = end_pos - self._write_pos
                self._buffer[self._write_pos:end_pos] = data[:copy_len]
                self._write_pos = end_pos

                if self._chunk_callback and self._chunk_samples > 0:
                    self._samples_since_chunk += frames
                    if self._samples_since_chunk >= self._chunk_samples:
                        audio = self._buffer[:self._write_pos].copy()
                        self._samples_since_chunk = 0
                        self._chunk_callback(audio)

    def start(self, chunk_callback: Callable[[np.ndarray], None] | None = None, chunk_seconds: float = 0) -> None:
        with self._lock:
            self._write_pos = 0
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
            if self._write_pos == 0:
                return np.array([], dtype=DTYPE)
            audio = self._buffer[:self._write_pos].copy()
            self._write_pos = 0
            return audio

    def get_audio_so_far(self) -> np.ndarray:
        with self._lock:
            if self._write_pos == 0:
                return np.array([], dtype=DTYPE)
            return self._buffer[:self._write_pos].copy()

    @property
    def is_recording(self) -> bool:
        return self._recording


_recorder: AudioRecorder | None = None


def get_recorder() -> AudioRecorder:
    global _recorder
    if _recorder is None:
        _recorder = AudioRecorder()
    return _recorder
