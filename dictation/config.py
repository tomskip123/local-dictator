"""Configuration management for dictation app."""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal

CONFIG_DIR = Path.home() / ".config" / "dictation"
CONFIG_FILE = CONFIG_DIR / "config.json"

DeviceType = Literal["cpu", "cuda"]
ModelSize = Literal["tiny", "base", "small", "medium", "large-v3"]
HotkeyMode = Literal["hold", "toggle"]


@dataclass
class Config:
    device: DeviceType = "cpu"
    model: ModelSize = "tiny"
    language: str = "auto"
    hotkey: list[str] = field(default_factory=lambda: ["F10"])
    mode: HotkeyMode = "toggle"
    streaming: bool = True
    streaming_interval: float = 3.0
    silence_threshold: float = 0.005
    audio_normalize: bool = True
    audio_compress: bool = True
    audio_highpass: bool = True
    auto_punctuation: bool = True

    @classmethod
    def load(cls) -> "Config":
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2))


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def save_config() -> None:
    if _config is not None:
        _config.save()
