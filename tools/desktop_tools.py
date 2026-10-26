"""
Desktop and System Environment Automation Tools for JARVIS.

Provides tools to:
- Organize cluttered desktop files into categorized folders
- Change desktop wallpaper safely
- Inspect and configure system settings (theme, display, networking)
"""

from __future__ import annotations

import os
import sys
import shutil
import ctypes
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.base import BaseTool, ToolResult


class OrganizeDesktopTool(BaseTool):
    """Sorts messy desktop files into clean categorical folders."""
    name: str = "organize_desktop"
    description: str = (
        "Organizes cluttered files on the desktop into categorized folders: "
        "'Documents', 'Media', 'Code', 'Archives', 'Installers', and 'Misc'. Ignores shortcuts."
    )

    CATEGORIES = {
        "Documents": {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv", ".md"},
        "Media": {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mov", ".mp3", ".wav", ".webp", ".svg"},
        "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".sql", ".sh", ".rs", ".cpp", ".c"},
        "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
        "Installers": {".exe", ".msi", ".dmg", ".pkg", ".iso"}
    }

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "dry_run": {
                        "type": "boolean",
                        "description": "If true, reports planned moves without modifying the filesystem."
                    }
                },
                "required": []
            }
        }

    def run(self, dry_run: bool = False, **kwargs) -> ToolResult:
        try:
            desktop_path = Path.home() / "Desktop"
            if not desktop_path.exists():
                return ToolResult(success=False, message="Desktop directory not found.")

            moved_counts: Dict[str, int] = {cat: 0 for cat in self.CATEGORIES}
            moved_counts["Misc"] = 0
            actions_taken = []

            for item in desktop_path.iterdir():
                if item.is_dir() or item.name.startswith((".", "~$")) or item.suffix.lower() == ".lnk":
                    continue

                ext = item.suffix.lower()
                target_cat = "Misc"
                for cat, extensions in self.CATEGORIES.items():
                    if ext in extensions:
                        target_cat = cat
                        break

                target_dir = desktop_path / target_cat
                if not dry_run:
                    target_dir.mkdir(exist_ok=True)
                    dest = target_dir / item.name
                    # If destination exists, generate collision-free name
                    if dest.exists():
                        dest = target_dir / f"{item.stem}_{int(os.path.getmtime(item))}{item.suffix}"
                    shutil.move(str(item), str(dest))

                moved_counts[target_cat] += 1
                actions_taken.append(f"{item.name} -> {target_cat}/")

            total = sum(moved_counts.values())
            summary = ", ".join(f"{k}: {v}" for k, v in moved_counts.items() if v > 0) or "Desktop is already clean"
            prefix = "[Dry Run] " if dry_run else ""

            return ToolResult(
                success=True,
                data={"total_organized": total, "breakdown": moved_counts, "dry_run": dry_run},
                message=f"{prefix}Desktop organized: {total} files sorted ({summary})."
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                message=f"Desktop organization failed: {str(exc)}"
            )


class SetWallpaperTool(BaseTool):
    """Changes the desktop wallpaper."""
    name: str = "set_wallpaper"
    description: str = "Sets the user's desktop wallpaper to a specified local image file."

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Absolute path to the image file (JPG, PNG, or BMP)."
                    }
                },
                "required": ["image_path"]
            }
        }

    def run(self, image_path: str, **kwargs) -> ToolResult:
        try:
            p = Path(image_path).resolve()
            if not p.exists() or not p.is_file():
                return ToolResult(success=False, message=f"Wallpaper image file does not exist: {image_path}")

            if sys.platform == "win32":
                SPI_SETDESKWALLPAPER = 20
                SPIF_UPDATEINIFILE = 0x01
                SPIF_SENDCHANGE = 0x02
                res = ctypes.windll.user32.SystemParametersInfoW(
                    SPI_SETDESKWALLPAPER,
                    0,
                    str(p),
                    SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
                )
                if res:
                    return ToolResult(
                        success=True,
                        data={"image_path": str(p)},
                        message=f"Desktop wallpaper updated to: {p.name}"
                    )
                return ToolResult(success=False, message="Windows API rejected wallpaper update.")
            else:
                return ToolResult(success=False, message="Wallpaper change only supported on Windows.")
        except Exception as exc:
            return ToolResult(success=False, message=f"Failed to set wallpaper: {str(exc)}")


class ComputerSettingsTool(BaseTool):
    """Inspects and configures operating system settings."""
    name: str = "computer_settings"
    description: str = "Inspects or toggles system settings: theme (dark/light), network adapters, and screen resolution."

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "setting": {
                        "type": "string",
                        "enum": ["theme", "network", "resolution"],
                        "description": "Setting category to query or adjust."
                    },
                    "value": {
                        "type": "string",
                        "description": "Optional value for the setting (e.g. 'dark', 'light')."
                    }
                },
                "required": ["setting"]
            }
        }

    def run(self, setting: str, value: Optional[str] = None, **kwargs) -> ToolResult:
        cat = setting.lower().strip()
        try:
            if cat == "theme":
                if value and value.lower() in ("dark", "light"):
                    dark_mode = 1 if value.lower() == "dark" else 0
                    if sys.platform == "win32":
                        import winreg
                        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 0 if dark_mode else 1)
                            winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 0 if dark_mode else 1)
                        return ToolResult(success=True, data={"theme": value.lower()}, message=f"System theme switched to {value.lower()} mode.")
                return ToolResult(success=True, message="Theme query returned active Windows profile.")

            elif cat == "network":
                import psutil
                stats = psutil.net_if_stats()
                active = [name for name, s in stats.items() if s.isup]
                return ToolResult(
                    success=True,
                    data={"active_adapters": active},
                    message=f"Active network interfaces: {', '.join(active)}"
                )

            elif cat == "resolution":
                import ctypes
                user32 = ctypes.windll.user32
                w = user32.GetSystemMetrics(0)
                h = user32.GetSystemMetrics(1)
                return ToolResult(
                    success=True,
                    data={"width": w, "height": h},
                    message=f"Primary display resolution: {w}x{h}"
                )

            return ToolResult(success=False, message=f"Unrecognized setting: {setting}")
        except Exception as exc:
            return ToolResult(success=False, message=f"Settings operation failed: {str(exc)}")
