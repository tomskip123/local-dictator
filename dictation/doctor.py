"""Diagnostic and maintenance tools for dictation."""

import shutil
import subprocess
import sys
from pathlib import Path


CACHE_DIR = Path.home() / ".cache" / "whisper"


def get_cache_size() -> tuple[str, int]:
    """Get cache size as human readable string and file count."""
    if not CACHE_DIR.exists():
        return "0B", 0

    total = sum(f.stat().st_size for f in CACHE_DIR.iterdir() if f.is_file())
    count = len(list(CACHE_DIR.iterdir()))

    for unit in ["B", "KB", "MB", "GB"]:
        if total < 1024:
            return f"{total:.1f}{unit}", count
        total /= 1024
    return f"{total:.1f}TB", count


def cmd_cache():
    """Show cache information."""
    size, count = get_cache_size()
    print(f"Whisper model cache: {size} ({count} file(s))")
    print(f"Location: {CACHE_DIR}")

    if CACHE_DIR.exists():
        print()
        for f in sorted(CACHE_DIR.iterdir()):
            if f.is_file():
                fsize = f.stat().st_size / (1024 * 1024)
                print(f"  {f.name}: {fsize:.0f}MB")


def cmd_clean():
    """Clean the model cache."""
    size, count = get_cache_size()

    if count == 0:
        print("No cache to clean.")
        return

    print(f"Whisper model cache: {size} ({count} file(s))")
    print(f"Location: {CACHE_DIR}")
    print()

    confirm = input("Delete all cached models? [y/N] ").strip().lower()
    if confirm == "y":
        shutil.rmtree(CACHE_DIR)
        print("Cache cleared.")
    else:
        print("Cancelled.")


def cmd_status():
    """Show service status."""
    print("Services:")
    for service in ["ydotoold", "dictation"]:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", service],
            capture_output=True,
            text=True,
        )
        status = result.stdout.strip()
        symbol = "✓" if status == "active" else "✗"
        print(f"  {symbol} {service}: {status}")


def cmd_logs():
    """Show recent logs."""
    for service in ["ydotoold", "dictation"]:
        print(f"=== {service} ===")
        subprocess.run([
            "journalctl", "--user", "-u", service, "-n", "10", "--no-pager"
        ])
        print()


def main():
    """Main entry point."""
    args = sys.argv[1:]

    if not args or args[0] in ["-h", "--help", "help"]:
        print("Usage: dictation-doctor <command>")
        print()
        print("Commands:")
        print("  status    Show service status")
        print("  logs      Show recent logs")
        print("  cache     Show cache size")
        print("  clean     Delete cached models")
        return 0

    cmd = args[0]

    if cmd == "cache":
        cmd_cache()
    elif cmd == "clean":
        cmd_clean()
    elif cmd == "status":
        cmd_status()
    elif cmd == "logs":
        cmd_logs()
    else:
        print(f"Unknown command: {cmd}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
