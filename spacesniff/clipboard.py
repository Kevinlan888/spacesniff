from __future__ import annotations

import shutil
import subprocess


def copy_to_clipboard(text: str) -> tuple[bool, str]:
    """Copy text to the system clipboard using common platform tools."""
    commands = [
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["pbcopy"],
        ["clip.exe"],
    ]
    for command in commands:
        if shutil.which(command[0]) is None:
            continue
        try:
            subprocess.run(
                command,
                input=text,
                text=True,
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"clipboard command failed: {exc}"
        return True, "path copied to clipboard"
    return False, "no clipboard command available"
