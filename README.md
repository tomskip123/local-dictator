# Dictation

Dictation for Linux that respects your privacy. Uses OpenAI Whisper to transcribe speech locally on your machine - nothing is sent to the cloud. Just press F10, speak, and watch your words appear in any application. Designed for Wayland with streaming transcription support, so you see words as you speak them. Works with CPU or GPU (CUDA) acceleration.

## Features

- **Local processing** - no cloud services, works offline
- **Streaming mode** - see words as you speak
- **CUDA support** - GPU acceleration for faster transcription
- **Configurable hotkey** - hold-to-talk or toggle modes
- **Audio processing** - normalization, compression, high-pass filter
- **Settings GUI** - configure everything visually

## Requirements

- Linux with Wayland or X11
- Python 3.10+
- `ydotool` for text injection
- GTK4 and libadwaita (for settings GUI)

## Installation

### 1. Install system dependencies

**Arch Linux:**
```bash
sudo pacman -S ydotool python-pipx python-gobject gtk4 libadwaita
```

**Ubuntu/Debian:**
```bash
sudo apt install ydotool pipx python3-gi gtk4 libadwaita-1-0
```

### 2. Add user to input group

```bash
sudo usermod -aG input $USER
```

Log out and back in (or reboot) for group changes to take effect.

### 3. Clone and install

```bash
git clone https://github.com/tomskip123/linux-dictator.git
cd linux-dictator
./install.sh
```

This installs the Python package and sets up systemd services.

### 4. Start services

```bash
systemctl --user start ydotoold
systemctl --user start dictation
```

Or reboot and they'll start automatically.

## Usage

**Default hotkey:** `F10` (toggle mode)

1. Press `F10` to start recording
2. Speak
3. Press `F10` again to stop
4. Text appears at your cursor

### Commands

| Command | Description |
|---------|-------------|
| `dictation` | Run the dictation service (usually via systemd) |
| `dictation-settings` | Open the settings GUI |
| `dictation-doctor cache` | Show cached model sizes |
| `dictation-doctor clean` | Delete cached models to free space |
| `dictation-doctor status` | Check service status |
| `dictation-doctor logs` | View recent logs |

### Shell script helpers

```bash
./doctor.sh          # Run diagnostics
./doctor.sh restart  # Restart services
./doctor.sh logs     # View logs
./doctor.sh clean    # Clear model cache
```

## Configuration

Configuration is stored in `~/.config/dictation/config.json`:

```json
{
  "device": "cpu",
  "model": "small",
  "language": "auto",
  "hotkey": ["F10"],
  "mode": "toggle",
  "streaming": true,
  "streaming_interval": 3.0,
  "silence_threshold": 0.005,
  "audio_normalize": true,
  "audio_compress": true,
  "audio_highpass": true
}
```

### Options

| Option | Values | Description |
|--------|--------|-------------|
| `device` | `cpu`, `cuda` | Processing device |
| `model` | `tiny`, `base`, `small`, `medium`, `large-v3` | Whisper model size |
| `language` | `auto`, `en`, `es`, etc. | Language code or auto-detect |
| `hotkey` | Key names | Activation key(s) |
| `mode` | `hold`, `toggle` | Hold-to-talk or toggle |
| `streaming` | `true`, `false` | Show words as you speak |
| `streaming_interval` | seconds | How often to update (streaming mode) |
| `silence_threshold` | 0.001-0.02 | Audio level to filter as silence |
| `audio_normalize` | `true`, `false` | Normalize audio levels |
| `audio_compress` | `true`, `false` | Apply dynamic compression |
| `audio_highpass` | `true`, `false` | Filter low frequency rumble |

### Model sizes

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | 75MB | Fastest | Basic |
| base | 150MB | Fast | Good |
| small | 500MB | Medium | Better |
| medium | 1.5GB | Slow | Great |
| large-v3 | 3GB | Slowest | Best |

Models are downloaded automatically on first use and cached in `~/.cache/whisper/`.

## Troubleshooting

Run diagnostics:
```bash
./doctor.sh
```

### Common issues

**"Permission denied" or hotkey not working:**
- Ensure you're in the `input` group: `groups | grep input`
- Reboot after adding yourself to the group

**ydotool socket missing:**
```bash
systemctl --user restart ydotoold
```

**Text not appearing:**
- Check that ydotoold is running: `systemctl --user status ydotoold`
- Verify the socket exists: `ls /run/user/$UID/.ydotool_socket`

**"Thank you" appearing randomly:**
- Raise the silence threshold in settings
- This is a Whisper hallucination on quiet audio

**High CPU usage:**
- Use a smaller model (`tiny` or `base`)
- Enable CUDA if you have an NVIDIA GPU

### View logs

```bash
journalctl --user -u dictation -f
journalctl --user -u ydotoold -f
```

## Uninstalling

```bash
./uninstall.sh
```

This removes the systemd services and Python package. Model cache remains in `~/.cache/whisper/` - delete manually if desired.

## License

MIT
