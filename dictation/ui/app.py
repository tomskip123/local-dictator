"""GTK4 Application for dictation."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib

from .settings import SettingsWindow


class DictationApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.local.dictation")
        self.settings_window: SettingsWindow | None = None

    def do_activate(self) -> None:
        self.show_settings()

    def show_settings(self) -> None:
        if self.settings_window is None or not self.settings_window.get_visible():
            self.settings_window = SettingsWindow(application=self)
        self.settings_window.present()

    def quit_app(self) -> None:
        self.quit()


def main() -> int:
    app = DictationApp()
    return app.run()
