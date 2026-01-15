#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOURCES="$SCRIPT_DIR/dictation/resources"

echo "=== Dictation Installer ==="
echo

# Check dependencies
echo "Checking dependencies..."
missing=()
command -v ydotool >/dev/null || missing+=("ydotool")
command -v pipx >/dev/null || missing+=("python-pipx")

if [ ${#missing[@]} -ne 0 ]; then
    echo "Missing dependencies: ${missing[*]}"
    echo
    echo "Install with:"
    echo "  Arch:   sudo pacman -S ${missing[*]}"
    echo "  Ubuntu: sudo apt install ${missing[*]}"
    exit 1
fi

# Check input group membership
echo "Checking permissions..."
if ! groups | grep -q '\binput\b'; then
    echo
    echo "WARNING: You are not in the 'input' group."
    echo "This is required for hotkey detection and text injection."
    echo
    read -p "Add yourself to the input group now? [Y/n] " confirm
    if [[ ! "$confirm" =~ ^[Nn]$ ]]; then
        sudo usermod -aG input "$USER"
        echo "Added to input group. You MUST log out and back in (or reboot) for this to take effect."
        echo
    else
        echo "Skipped. Run 'sudo usermod -aG input \$USER' manually, then log out/in."
        echo
    fi
fi

# Install Python package with pipx
echo "Installing Python package..."
pipx install -e "$SCRIPT_DIR" --force
pipx inject dictation PyGObject

# Install desktop entry for settings
echo "Installing desktop entry..."
mkdir -p ~/.local/share/applications
cp "$RESOURCES/dictation-settings.desktop" ~/.local/share/applications/

# Install systemd services
echo "Installing systemd services..."
mkdir -p ~/.config/systemd/user
cp "$RESOURCES/ydotoold.service" ~/.config/systemd/user/
cp "$RESOURCES/dictation.service" ~/.config/systemd/user/

# Reload and enable services
echo "Enabling services..."
systemctl --user daemon-reload
systemctl --user enable ydotoold.service
systemctl --user enable dictation.service

echo
echo "=== Installation complete ==="
echo
echo "To start now:"
echo "  systemctl --user start ydotoold"
echo "  systemctl --user start dictation"
echo
echo "Or reboot and services will start automatically."
echo
if ! groups | grep -q '\binput\b'; then
    echo "IMPORTANT: Log out and back in for input group permissions to take effect!"
    echo
fi
echo "Hotkey: F10 (toggle recording)"
echo "Settings: dictation-settings"
echo "Diagnostics: dictation-doctor status"
echo "Config: ~/.config/dictation/config.json"
