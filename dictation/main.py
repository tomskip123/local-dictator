"""Main entry point for dictation app."""

import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np

from .config import get_config
from .audio import get_recorder
from .transcriber import transcribe, get_model
from .injector import inject_text, delete_chars
from .hotkeys import HotkeyListener
from .ui.indicator import StatusIndicator


class DictationController:
    def __init__(self):
        self.indicator = StatusIndicator()
        self.recorder = get_recorder()
        self._toggle_recording = False
        self._running = True
        self._last_text = ""
        self._streaming_active = False
        self._transcribe_lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)

        config = get_config()
        self.listener = HotkeyListener(
            hotkey=config.hotkey,
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )

    def _on_hotkey_press(self) -> None:
        config = get_config()
        if config.mode == "hold":
            self._start_recording()
        else:
            if self._toggle_recording:
                self._stop_and_transcribe()
                self._toggle_recording = False
            else:
                self._start_recording()
                self._toggle_recording = True

    def _on_hotkey_release(self) -> None:
        config = get_config()
        if config.mode == "hold":
            self._stop_and_transcribe()

    def _on_audio_chunk(self, audio: np.ndarray) -> None:
        if not self._streaming_active:
            return
        if not self._transcribe_lock.acquire(blocking=False):
            return

        def do_chunk_transcribe():
            try:
                if self._streaming_active:
                    text = transcribe(audio)
                    if self._streaming_active and text:
                        self._update_streaming_text(text)
            finally:
                self._transcribe_lock.release()

        self._executor.submit(do_chunk_transcribe)

    def _update_streaming_text(self, new_text: str) -> None:
        if not new_text:
            return

        old_words = self._last_text.split()
        new_words = new_text.split()

        # Find common word prefix (more stable than character-based)
        common_count = 0
        for i in range(min(len(old_words), len(new_words))):
            if old_words[i] == new_words[i]:
                common_count = i + 1
            else:
                break

        # What needs to change
        stable_part = " ".join(new_words[:common_count])
        old_suffix = " ".join(old_words[common_count:])
        new_suffix = " ".join(new_words[common_count:])

        # Calculate chars to delete (old suffix + space before it)
        chars_to_delete = len(old_suffix)
        if old_suffix and stable_part:
            chars_to_delete += 1

        # Calculate text to add (new suffix + space before it)
        if new_suffix:
            text_to_add = (" " + new_suffix) if stable_part else new_suffix
        else:
            text_to_add = ""

        if chars_to_delete > 0:
            delete_chars(chars_to_delete)
        if text_to_add:
            inject_text(text_to_add)

        self._last_text = new_text

    def _start_recording(self) -> None:
        config = get_config()
        print("Recording...")
        self.indicator.set_status("recording")
        self._last_text = ""

        if config.streaming:
            self._streaming_active = True
            self.recorder.start(
                chunk_callback=self._on_audio_chunk,
                chunk_seconds=config.streaming_interval,
            )
        else:
            self.recorder.start()

    def _stop_and_transcribe(self) -> None:
        config = get_config()
        self._streaming_active = False
        audio = self.recorder.stop()

        if config.streaming:
            # Wait for any in-flight transcription to finish
            with self._transcribe_lock:
                self._last_text = ""
            self.indicator.set_status("idle")
            return

        print("Transcribing...")
        self.indicator.set_status("transcribing")

        def do_transcribe():
            self._inject_result(transcribe(audio))

        self._executor.submit(do_transcribe)

    def _inject_result(self, text: str) -> None:
        if text:
            print(f"Injecting: {text}")
            inject_text(text)
        else:
            print("No speech detected")
        self.indicator.set_status("idle")

    def run(self) -> int:
        print("Loading Whisper model (this may take a moment on first run)...")
        get_model()
        print("Model loaded.")

        if not self.listener.start(debug=False):
            return 1

        config = get_config()
        mode_desc = "hold to talk" if config.mode == "hold" else "toggle"
        stream_desc = " (streaming)" if config.streaming else ""
        hotkey_str = " + ".join(config.hotkey)
        print(f"Dictation ready. Press {hotkey_str} ({mode_desc}{stream_desc}) to dictate.")
        print("Press Ctrl+C to quit.")

        def handle_signal(sig, frame):
            print("\nShutting down...")
            self._running = False
            self.listener.stop()
            self._executor.shutdown(wait=False)
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        while self._running:
            signal.pause()

        return 0


def main() -> int:
    controller = DictationController()
    return controller.run()


if __name__ == "__main__":
    raise SystemExit(main())
