# Windows Support Update

Date: 2026-05-26

## Summary

Added first-class Windows documentation and standalone build support for the terminal SpaceSniffer tool.

## Delivered

- Added `scripts/build-standalone.ps1` for Windows PowerShell packaging with PyInstaller.
- Kept the existing Linux/macOS shell packaging script for Unix-like environments.
- Expanded `README.md` with platform-specific setup, usage, verification, and standalone build instructions.
- Documented current Windows expectations for clipboard support and executable packaging.

## Notes

- Windows requires building `spacesniff.exe` on a Windows machine.
- The existing Linux standalone binary is not portable to Windows.
- Clipboard copy already attempts `clip.exe`, so no code change was required for the first Windows pass.
