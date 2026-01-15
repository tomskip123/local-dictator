#!/bin/bash
set -e

echo "=== Dictation Uninstaller ==="
echo

# Stop and disable services
echo "Stopping services..."
systemctl --user stop dictation.service 2>/dev/null || true
systemctl --user disable dictation.service 2>/dev/null || true

# Remove systemd services
echo "Removing systemd services..."
rm -f ~/.config/systemd/user/dictation.service
systemctl --user daemon-reload

# Remove desktop entries
echo "Removing desktop entries..."
rm -f ~/.local/share/applications/dictation.desktop
rm -f ~/.local/share/applications/dictation-settings.desktop

# Uninstall Python package
echo "Uninstalling Python package..."
pipx uninstall dictation 2>/dev/null || true

echo
echo "=== Uninstall complete ==="
echo
echo "Note: ydotoold service was left in place (may be used by other apps)"
echo "Config left at: ~/.config/dictation/"
