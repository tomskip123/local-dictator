"""Settings window using Libadwaita."""

import threading
import numpy as np
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib

from ..config import get_config, save_config
from ..transcriber import cuda_available, reload_model
from ..audio import get_recorder


class SettingsWindow(Adw.PreferencesWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Dictation Settings")
        self.set_default_size(500, 400)

        config = get_config()

        # Transcription page
        transcription_page = Adw.PreferencesPage()
        transcription_page.set_title("Transcription")
        transcription_page.set_icon_name("audio-input-microphone-symbolic")

        # Device group
        device_group = Adw.PreferencesGroup()
        device_group.set_title("Processing")
        device_group.set_description("Choose CPU or GPU for transcription")

        self.device_row = Adw.ComboRow()
        self.device_row.set_title("Device")
        self.device_row.set_subtitle("CUDA provides faster transcription" if cuda_available() else "CUDA not available")

        device_model = Gtk.StringList.new(["CPU", "CUDA"])
        self.device_row.set_model(device_model)
        self.device_row.set_selected(0 if config.device == "cpu" else 1)
        self.device_row.set_sensitive(cuda_available())
        self.device_row.connect("notify::selected", self._on_device_changed)
        device_group.add(self.device_row)

        # Model group
        model_group = Adw.PreferencesGroup()
        model_group.set_title("Model")
        model_group.set_description("Larger models are more accurate but slower")

        self.model_row = Adw.ComboRow()
        self.model_row.set_title("Model Size")

        models = ["tiny", "base", "small", "medium", "large-v3"]
        model_model = Gtk.StringList.new(models)
        self.model_row.set_model(model_model)
        self.model_row.set_selected(models.index(config.model))
        self.model_row.connect("notify::selected", self._on_model_changed)
        model_group.add(self.model_row)

        # Language
        self.language_row = Adw.EntryRow()
        self.language_row.set_title("Language")
        self.language_row.set_text(config.language)
        self.language_row.connect("changed", self._on_language_changed)
        model_group.add(self.language_row)

        # Audio group
        audio_group = Adw.PreferencesGroup()
        audio_group.set_title("Audio")
        audio_group.set_description("Microphone sensitivity settings")

        self.silence_row = Adw.ActionRow()
        self.silence_row.set_title("Silence Threshold")
        self.silence_row.set_subtitle("Higher = filters more background noise")

        self.silence_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0.001, 0.02, 0.001
        )
        self.silence_scale.set_value(config.silence_threshold)
        self.silence_scale.set_size_request(200, -1)
        self.silence_scale.set_valign(Gtk.Align.CENTER)
        self.silence_scale.connect("value-changed", self._on_silence_changed)
        self.silence_row.add_suffix(self.silence_scale)
        audio_group.add(self.silence_row)

        # Audio level meter
        self.level_row = Adw.ActionRow()
        self.level_row.set_title("Microphone Level")
        self.level_row.set_subtitle("Current input level vs threshold")

        level_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        level_box.set_valign(Gtk.Align.CENTER)

        self.level_bar = Gtk.LevelBar()
        self.level_bar.set_min_value(0)
        self.level_bar.set_max_value(0.02)
        self.level_bar.set_value(0)
        self.level_bar.set_size_request(200, 8)
        self.level_bar.add_offset_value("threshold", config.silence_threshold)
        level_box.append(self.level_bar)

        self.level_label = Gtk.Label(label="--")
        self.level_label.add_css_class("caption")
        level_box.append(self.level_label)

        self.level_row.add_suffix(level_box)
        audio_group.add(self.level_row)

        # Audio processing toggles
        processing_group = Adw.PreferencesGroup()
        processing_group.set_title("Audio Processing")
        processing_group.set_description("Improve transcription quality")

        self.normalize_row = Adw.SwitchRow()
        self.normalize_row.set_title("Normalize")
        self.normalize_row.set_subtitle("Scale audio to consistent level")
        self.normalize_row.set_active(config.audio_normalize)
        self.normalize_row.connect("notify::active", self._on_normalize_changed)
        processing_group.add(self.normalize_row)

        self.compress_row = Adw.SwitchRow()
        self.compress_row.set_title("Compress")
        self.compress_row.set_subtitle("Reduce dynamic range for consistent volume")
        self.compress_row.set_active(config.audio_compress)
        self.compress_row.connect("notify::active", self._on_compress_changed)
        processing_group.add(self.compress_row)

        self.highpass_row = Adw.SwitchRow()
        self.highpass_row.set_title("High-pass Filter")
        self.highpass_row.set_subtitle("Remove low frequency rumble")
        self.highpass_row.set_active(config.audio_highpass)
        self.highpass_row.connect("notify::active", self._on_highpass_changed)
        processing_group.add(self.highpass_row)

        # Start audio monitoring
        self._monitoring = True
        self._start_audio_monitor()
        self.connect("close-request", self._on_close)

        transcription_page.add(device_group)
        transcription_page.add(model_group)
        transcription_page.add(audio_group)
        transcription_page.add(processing_group)

        # Hotkey page
        hotkey_page = Adw.PreferencesPage()
        hotkey_page.set_title("Hotkey")
        hotkey_page.set_icon_name("preferences-desktop-keyboard-symbolic")

        hotkey_group = Adw.PreferencesGroup()
        hotkey_group.set_title("Activation")

        self.mode_row = Adw.ComboRow()
        self.mode_row.set_title("Mode")
        self.mode_row.set_subtitle("How the hotkey activates dictation")
        mode_model = Gtk.StringList.new(["Hold to talk", "Toggle"])
        self.mode_row.set_model(mode_model)
        self.mode_row.set_selected(0 if config.mode == "hold" else 1)
        self.mode_row.connect("notify::selected", self._on_mode_changed)
        hotkey_group.add(self.mode_row)

        hotkey_display = Adw.ActionRow()
        hotkey_display.set_title("Current Hotkey")
        hotkey_display.set_subtitle(" + ".join(config.hotkey))
        hotkey_group.add(hotkey_display)

        hotkey_page.add(hotkey_group)

        self.add(transcription_page)
        self.add(hotkey_page)

    def _reload_model_with_progress(self) -> None:
        dialog = Adw.MessageDialog(
            transient_for=self,
            modal=True,
            heading="Loading Model",
            body="Downloading and loading model, please wait...",
        )
        spinner = Gtk.Spinner()
        spinner.set_size_request(32, 32)
        spinner.start()
        dialog.set_extra_child(spinner)
        dialog.set_close_response("")
        dialog.present()

        def do_reload():
            reload_model()
            GLib.idle_add(dialog.close)

        thread = threading.Thread(target=do_reload, daemon=True)
        thread.start()

    def _on_device_changed(self, row, _) -> None:
        config = get_config()
        config.device = "cpu" if row.get_selected() == 0 else "cuda"
        save_config()
        self._reload_model_with_progress()

    def _on_model_changed(self, row, _) -> None:
        config = get_config()
        models = ["tiny", "base", "small", "medium", "large-v3"]
        config.model = models[row.get_selected()]
        save_config()
        self._reload_model_with_progress()

    def _on_language_changed(self, row) -> None:
        config = get_config()
        config.language = row.get_text() or "auto"
        save_config()

    def _on_mode_changed(self, row, _) -> None:
        config = get_config()
        config.mode = "hold" if row.get_selected() == 0 else "toggle"
        save_config()

    def _on_silence_changed(self, scale) -> None:
        config = get_config()
        config.silence_threshold = round(scale.get_value(), 4)
        save_config()
        self.level_bar.add_offset_value("threshold", config.silence_threshold)

    def _start_audio_monitor(self) -> None:
        import sounddevice as sd

        def audio_callback(indata, frames, time, status):
            if not self._monitoring:
                return
            rms = np.sqrt(np.mean(indata**2))
            GLib.idle_add(self._update_level, rms)

        self._stream = sd.InputStream(
            channels=1,
            samplerate=16000,
            blocksize=1600,
            callback=audio_callback,
        )
        self._stream.start()

    def _update_level(self, rms: float) -> None:
        self.level_bar.set_value(min(rms, 0.02))
        threshold = self.silence_scale.get_value()
        status = "✓ Sound" if rms > threshold else "Silent"
        self.level_label.set_text(f"{rms:.4f} ({status})")

    def _on_normalize_changed(self, row, _) -> None:
        config = get_config()
        config.audio_normalize = row.get_active()
        save_config()

    def _on_compress_changed(self, row, _) -> None:
        config = get_config()
        config.audio_compress = row.get_active()
        save_config()

    def _on_highpass_changed(self, row, _) -> None:
        config = get_config()
        config.audio_highpass = row.get_active()
        save_config()

    def _on_close(self, *args) -> None:
        self._monitoring = False
        if hasattr(self, "_stream"):
            self._stream.stop()
            self._stream.close()
