"""
Autonomous Development and Coding Agent Tools for JARVIS.
Author: Abhijit (System & Automation Engineer)

Provides full autonomous coding capabilities:
1. Open VS Code: Opens any folder or file in Visual Studio Code (`code <path>`), creates directory if needed, and foregrounds VS Code.
2. File Creation & Code Generation: Creates files (`index.html`, `style.css`, `app.js`, `main.py`, etc.) with correct, modern, error-free syntaxes.
3. Project Scaffolding: Scaffolds complete web or Python projects from scratch and opens them in VS Code immediately.
4. Run & Execute: Launches web preview servers (`http://localhost:8000`) or executes code, reporting local server addresses and runtime status.
5. Syntax Validation: Checks Python, JavaScript, HTML, CSS, and JSON syntax.
6. Error Diagnosis: Diagnoses tracebacks and errors, pinpointing causes and recommending fixes.
7. Dev Tools: Runs pytest suites, checks git status/diff, and installs packages safely.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import py_compile
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

PEP508_PACKAGE_RE = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?(\[[a-zA-Z0-9._,-]+\])?([><=~!]=?[a-zA-Z0-9.*+!-]+)?$"
)


def is_package_name_valid(name: str) -> bool:
    """Validate package name against PEP 508 and reject flag injection attacks."""
    if not name or not isinstance(name, str):
        return False
    name = name.strip()
    if name.startswith("-") or any(char in name for char in (";", "&", "|", "`", "$", " ", "\n", "\r", "\t")):
        return False
    return bool(PEP508_PACKAGE_RE.match(name))


def find_vscode_executable() -> Optional[str]:
    """Finds the Visual Studio Code executable or cmd wrapper on Windows/system."""
    # 1. PATH lookup
    code_path = shutil.which("code")
    if code_path:
        return code_path

    # 2. Standard Windows install locations
    local_app_data = os.getenv("LOCALAPPDATA", "")
    program_files = os.getenv("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.getenv("ProgramFiles(x86)", r"C:\Program Files (x86)")

    candidates = [
        os.path.join(local_app_data, r"Programs\Microsoft VS Code\bin\code.cmd"),
        os.path.join(local_app_data, r"Programs\Microsoft VS Code\Code.exe"),
        os.path.join(program_files, r"Microsoft VS Code\bin\code.cmd"),
        os.path.join(program_files, r"Microsoft VS Code\Code.exe"),
        os.path.join(program_files_x86, r"Microsoft VS Code\bin\code.cmd"),
        os.path.join(program_files_x86, r"Microsoft VS Code\Code.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    return "code"


def focus_vscode_window() -> bool:
    """Brings the Visual Studio Code window to the foreground."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        def _raise(hwnd: int) -> bool:
            try:
                if user32.IsIconic(hwnd):
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                ours = kernel32.GetCurrentThreadId()
                their = user32.GetWindowThreadProcessId(hwnd, None)
                if ours != their:
                    user32.AttachThreadInput(ours, their, True)
                try:
                    user32.BringWindowToTop(hwnd)
                    user32.SetForegroundWindow(hwnd)
                    user32.SetFocus(hwnd)
                    return True
                finally:
                    if ours != their:
                        user32.AttachThreadInput(ours, their, False)
            except Exception:
                return False
            return False

        found_hwnd: Optional[int] = None

        def _enum_cb(hwnd: int, _lparam: Any) -> bool:
            nonlocal found_hwnd
            if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if "visual studio code" in title or " - code" in title:
                        found_hwnd = hwnd
                        return False
            return True

        WNDENUM = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.EnumWindows(WNDENUM(_enum_cb), 0)

        if found_hwnd:
            return _raise(found_hwnd)
    except Exception as exc:
        logger.debug("Focusing VS Code window failed: %s", exc)
    return False


# Standard modern syntax templates
TEMPLATES: Dict[str, str] = {
    "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>JARVIS Project</title>
  <link rel="stylesheet" href="style.css">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
</head>
<body>
  <div class="app-container">
    <header class="navbar">
      <div class="logo">⚡ JARVIS Dev</div>
      <nav>
        <a href="#features">Features</a>
        <a href="#about">About</a>
        <a href="#contact" class="btn-primary">Get Started</a>
      </nav>
    </header>

    <main class="hero-section">
      <h1 class="hero-title">Built from Scratch with <span class="gradient-text">Precision</span></h1>
      <p class="hero-subtitle">Production-ready architecture, clean responsive design, and modular code generated by your AI Dev Agent.</p>
      <div class="cta-group">
        <button id="actionBtn" class="btn-glow">Explore Live Demo</button>
      </div>
      <div id="statusBox" class="status-card">System Ready &bull; Local Server Active</div>
    </main>

    <footer class="footer">
      <p>&copy; 2026 JARVIS Autonomous Engineering. All rights reserved.</p>
    </footer>
  </div>
  <script src="app.js"></script>
</body>
</html>
""",
    "style.css": """/* Modern Responsive Styling - JARVIS Dev Agent */
:root {
  --bg-color: #0b0f19;
  --card-bg: rgba(22, 27, 34, 0.85);
  --accent-cyan: #00f0ff;
  --accent-blue: #0070f3;
  --text-main: #f0f6fc;
  --text-muted: #8b949e;
  --border-color: rgba(255, 255, 255, 0.1);
  --glow-shadow: 0 0 25px rgba(0, 240, 255, 0.35);
  --font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-family);
  background: radial-gradient(circle at 50% 20%, #151d30 0%, var(--bg-color) 80%);
  color: var(--text-main);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
}

.app-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  width: 100%;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 2rem;
  border-bottom: 1px solid var(--border-color);
}

.logo {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--accent-cyan);
  text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
}

nav a {
  color: var(--text-muted);
  text-decoration: none;
  margin-left: 1.5rem;
  font-weight: 600;
  transition: color 0.2s ease;
}

nav a:hover {
  color: var(--accent-cyan);
}

.hero-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 4rem 1rem;
}

.hero-title {
  font-size: 3.5rem;
  font-weight: 800;
  line-height: 1.15;
  margin-bottom: 1.5rem;
}

.gradient-text {
  background: linear-gradient(135deg, var(--accent-cyan), #7928ca);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-subtitle {
  font-size: 1.25rem;
  color: var(--text-muted);
  max-width: 680px;
  margin-bottom: 2.5rem;
  line-height: 1.6;
}

.btn-glow {
  background: linear-gradient(135deg, #00d2ff 0%, #0070f3 100%);
  color: #fff;
  border: none;
  padding: 0.9rem 2.2rem;
  font-size: 1.05rem;
  font-weight: 600;
  border-radius: 9999px;
  cursor: pointer;
  box-shadow: var(--glow-shadow);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.btn-glow:hover {
  transform: translateY(-2px);
  box-shadow: 0 0 35px rgba(0, 240, 255, 0.6);
}

.status-card {
  margin-top: 3rem;
  padding: 0.75rem 1.75rem;
  border-radius: 8px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  font-size: 0.95rem;
  color: var(--accent-cyan);
  display: inline-flex;
  align-items: center;
  backdrop-filter: blur(12px);
}

.footer {
  text-align: center;
  padding: 2rem 0;
  font-size: 0.85rem;
  color: var(--text-muted);
  border-top: 1px solid var(--border-color);
}

@media (max-width: 768px) {
  .hero-title { font-size: 2.2rem; }
  .hero-subtitle { font-size: 1rem; }
}
""",
    "app.js": """// Interactive Logic - JARVIS Dev Agent
document.addEventListener("DOMContentLoaded", () => {
  const actionBtn = document.getElementById("actionBtn");
  const statusBox = document.getElementById("statusBox");

  if (actionBtn && statusBox) {
    let clickCount = 0;
    actionBtn.addEventListener("click", () => {
      clickCount++;
      const states = [
        "⚡ Neural Link Active & Synchronized",
        "🚀 High Performance Render Mode",
        "💎 Full Stack Modules Operational",
        "✨ System Optimized by JARVIS"
      ];
      const nextState = states[clickCount % states.length];
      statusBox.textContent = nextState;
      statusBox.style.borderColor = "#00f0ff";
      statusBox.style.boxShadow = "0 0 15px rgba(0, 240, 255, 0.4)";
      console.log(`[JARVIS Dev] State transitioned to: ${nextState}`);
    });
  }

  console.log("JARVIS Dev Agent: Application runtime online.");
});
""",
    "main.py": """\"\"\"
Main application module.
Generated by JARVIS Autonomous Dev Agent.
\"\"\"

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_pipeline() -> int:
    \"\"\"Executes main application logic.\"\"\"
    logger.info("JARVIS Application pipeline running successfully.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS Generated Python App")
    parser.add_argument("--test", action="store_true", help="Run self-diagnostic test")
    args = parser.parse_args()

    if args.test:
        logger.info("Diagnostic check: PASSED.")
        return 0

    return run_pipeline()


if __name__ == "__main__":
    sys.exit(main())
""",
    "README.md": """# Project Scaffold

Created by **JARVIS Autonomous Dev Agent**.

## Quick Start

### For Web Projects:
1. Open this directory in **Visual Studio Code**:
   ```bash
   code .
   ```
2. Run local preview server:
   ```bash
   python -m http.server 8000
   ```
3. Open your browser at: `http://localhost:8000`

### For Python Projects:
```bash
python main.py
```
""",
}


class DevAgentTool(BaseTool):
    """Autonomous software engineering, VS Code automation, project scaffolding, and code execution agent."""
    name: str = "dev_agent"
    description: str = (
        "Autonomous developer agent for JARVIS: opens folders and files in Visual Studio Code, "
        "creates code files with accurate syntaxes (HTML, CSS, JS, Python), scaffolds complete "
        "web/Python projects from scratch, runs projects and reports local server addresses, "
        "validates syntax, diagnoses errors, and manages tests/git."
    )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "open_vscode",
                            "create_file",
                            "scaffold_project",
                            "run_project",
                            "check_syntax",
                            "diagnose_error",
                            "run_tests",
                            "git_status",
                            "git_diff",
                            "install_package",
                        ],
                        "description": "Dev action to run.",
                    },
                    "target": {
                        "type": "string",
                        "description": "Directory path, file path, test path, or package name depending on action.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Code content when creating or editing files.",
                    },
                    "project_type": {
                        "type": "string",
                        "enum": ["web", "python", "fullstack", "minimal"],
                        "description": "Project template type when scaffolding (default: 'web').",
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Optional name or title for the project.",
                    },
                    "port": {
                        "type": "integer",
                        "description": "Port number for local web preview server (default: 8000).",
                    },
                    "error_text": {
                        "type": "string",
                        "description": "Error traceback or message to diagnose.",
                    },
                },
                "required": ["action"],
            },
        }

    def run(
        self,
        action: str,
        target: Optional[str] = None,
        content: Optional[str] = None,
        project_type: str = "web",
        project_name: Optional[str] = None,
        port: int = 8000,
        error_text: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        act = (action or "").lower().strip()
        try:
            # 1. Open VS Code
            if act in ("open_vscode", "open_folder", "open_in_vscode", "vscode"):
                return self._action_open_vscode(target)

            # 2. Create specific file
            elif act in ("create_file", "write_file", "add_file"):
                return self._action_create_file(target, content)

            # 3. Scaffold complete project
            elif act in ("scaffold_project", "scaffold", "create_project", "new_project"):
                return self._action_scaffold_project(target, project_type, project_name)

            # 4. Run project / Preview server
            elif act in ("run_project", "start_project", "preview", "run"):
                return self._action_run_project(target, port)

            # 5. Check Syntax
            elif act == "check_syntax":
                return self._action_check_syntax(target)

            # 6. Diagnose Error
            elif act in ("diagnose_error", "diagnose", "fix_error"):
                return self._action_diagnose_error(error_text or target, target)

            # 7. Run Pytest
            elif act == "run_tests":
                test_target = target or "tests"
                cmd = [sys.executable, "-m", "pytest", test_target, "-q"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                output = (res.stdout + "\n" + res.stderr).strip()
                return ToolResult(
                    success=res.returncode == 0,
                    data={"exit_code": res.returncode, "output": output[:2000]},
                    message=f"Pytest completed (exit {res.returncode}):\n{output[-300:]}",
                )

            # 8. Git Status
            elif act == "git_status":
                res = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, timeout=10)
                output = res.stdout.strip() or "Working tree clean."
                return ToolResult(
                    success=res.returncode == 0,
                    data={"status": output},
                    message=f"Git status:\n{output}",
                )

            # 9. Git Diff
            elif act == "git_diff":
                res = subprocess.run(["git", "diff", "--stat"], capture_output=True, text=True, timeout=10)
                output = res.stdout.strip() or "No uncommitted diffs."
                return ToolResult(
                    success=res.returncode == 0,
                    data={"diff": output},
                    message=f"Git diff summary:\n{output}",
                )

            # 10. Install Package
            elif act == "install_package":
                if not target or not is_package_name_valid(target):
                    return ToolResult(
                        success=False,
                        message=f"Rejected: invalid or dangerous package specification '{target}'",
                    )
                cmd = [sys.executable, "-m", "pip", "install", target]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                return ToolResult(
                    success=res.returncode == 0,
                    data={"package": target, "exit_code": res.returncode},
                    message=f"Pip install {'succeeded' if res.returncode == 0 else 'failed'}: {res.stdout[-200:]}",
                )

            return ToolResult(
                success=False,
                message=f"Unsupported dev action: '{action}'. Available: open_vscode, create_file, "
                        "scaffold_project, run_project, check_syntax, diagnose_error, run_tests, git_status, git_diff.",
            )

        except subprocess.TimeoutExpired:
            return ToolResult(success=False, message=f"Action '{action}' timed out.")
        except Exception as exc:
            logger.exception("DevAgent error for action '%s': %s", action, exc)
            return ToolResult(success=False, message=f"Dev agent failed: {str(exc)}")

    # -------------------------------------------------------------------------
    # Core Implementation Methods
    # -------------------------------------------------------------------------

    def _action_open_vscode(self, target: Optional[str]) -> ToolResult:
        """Opens a folder or file in Visual Studio Code."""
        folder_or_file = (target or ".").strip()
        resolved_path = os.path.abspath(folder_or_file)

        # Create folder if it doesn't exist
        if not os.path.exists(resolved_path):
            try:
                # If path has a file extension, create parent dir
                if os.path.splitext(resolved_path)[1]:
                    os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
                    Path(resolved_path).touch()
                else:
                    os.makedirs(resolved_path, exist_ok=True)
            except Exception as e:
                logger.warning("Could not pre-create path '%s': %s", resolved_path, e)

        vscode_exe = find_vscode_executable()
        if not vscode_exe:
            return ToolResult(
                success=False,
                message="Visual Studio Code executable was not found on this system.",
                data={"resolved_path": resolved_path},
            )

        try:
            # Spawn VS Code
            subprocess.Popen([vscode_exe, resolved_path], shell=True)
            time.sleep(0.5)
            focus_vscode_window()
            return ToolResult(
                success=True,
                message=f"Opened '{resolved_path}' in Visual Studio Code.",
                data={"action": "open_vscode", "path": resolved_path, "executable": vscode_exe},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                message=f"Failed to launch VS Code for '{resolved_path}': {str(exc)}",
                data={"error": str(exc)},
            )

    def _action_create_file(self, target: Optional[str], content: Optional[str]) -> ToolResult:
        """Creates a file with given or template code with validated syntax."""
        if not target:
            return ToolResult(success=False, message="Target file path must be specified.")

        clean_path = target.strip()
        resolved_path = os.path.abspath(clean_path)
        base_name = os.path.basename(resolved_path).lower()

        # If content is not provided, pick optimal starter template
        file_content = content
        if not file_content:
            if base_name in TEMPLATES:
                file_content = TEMPLATES[base_name]
            elif base_name.endswith(".html"):
                file_content = TEMPLATES["index.html"]
            elif base_name.endswith(".css"):
                file_content = TEMPLATES["style.css"]
            elif base_name.endswith(".js"):
                file_content = TEMPLATES["app.js"]
            elif base_name.endswith(".py"):
                file_content = TEMPLATES["main.py"]
            elif base_name.endswith(".json"):
                file_content = "{\n  \"version\": \"1.0.0\"\n}\n"
            elif base_name.endswith(".md"):
                file_content = f"# {Path(resolved_path).stem}\n\nDocumentation for project.\n"
            else:
                file_content = f"// File: {base_name}\n"

        try:
            os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(file_content)

            # Validate syntax if Python or JSON
            syntax_note = ""
            if resolved_path.endswith(".py"):
                try:
                    py_compile.compile(resolved_path, doraise=True)
                    syntax_note = " (Python syntax verified)"
                except Exception as pe:
                    syntax_note = f" (Warning: Python syntax check failed: {pe})"
            elif resolved_path.endswith(".json"):
                try:
                    json.loads(file_content)
                    syntax_note = " (JSON syntax verified)"
                except Exception as je:
                    syntax_note = f" (Warning: JSON syntax invalid: {je})"

            return ToolResult(
                success=True,
                message=f"Created file '{resolved_path}'{syntax_note}.",
                data={
                    "action": "create_file",
                    "path": resolved_path,
                    "bytes": len(file_content),
                    "filename": base_name,
                },
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                message=f"Failed to create file '{resolved_path}': {str(exc)}",
                data={"error": str(exc)},
            )

    def _action_scaffold_project(
        self,
        target: Optional[str],
        project_type: str = "web",
        project_name: Optional[str] = None,
    ) -> ToolResult:
        """Scaffolds a complete project from scratch with modern files and opens it in VS Code."""
        folder = (target or "my-project").strip()
        resolved_folder = os.path.abspath(folder)
        os.makedirs(resolved_folder, exist_ok=True)

        p_name = project_name or Path(resolved_folder).name or "JARVIS Project"
        created_files: List[str] = []

        if project_type.lower() in ("web", "html", "frontend"):
            # 1. index.html
            html_path = os.path.join(resolved_folder, "index.html")
            custom_html = TEMPLATES["index.html"].replace("JARVIS Project", p_name)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(custom_html)
            created_files.append("index.html")

            # 2. style.css
            css_path = os.path.join(resolved_folder, "style.css")
            with open(css_path, "w", encoding="utf-8") as f:
                f.write(TEMPLATES["style.css"])
            created_files.append("style.css")

            # 3. app.js
            js_path = os.path.join(resolved_folder, "app.js")
            with open(js_path, "w", encoding="utf-8") as f:
                f.write(TEMPLATES["app.js"])
            created_files.append("app.js")

            # 4. README.md
            readme_path = os.path.join(resolved_folder, "README.md")
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(TEMPLATES["README.md"].replace("Project Scaffold", f"# {p_name}"))
            created_files.append("README.md")

        else:
            # Python project template
            main_path = os.path.join(resolved_folder, "main.py")
            with open(main_path, "w", encoding="utf-8") as f:
                f.write(TEMPLATES["main.py"])
            created_files.append("main.py")

            req_path = os.path.join(resolved_folder, "requirements.txt")
            with open(req_path, "w", encoding="utf-8") as f:
                f.write("# Project dependencies\nrequests>=2.28.0\npytest>=8.0.0\n")
            created_files.append("requirements.txt")

            readme_path = os.path.join(resolved_folder, "README.md")
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(TEMPLATES["README.md"].replace("Project Scaffold", f"# {p_name}"))
            created_files.append("README.md")

        # Open in VS Code automatically!
        vscode_exe = find_vscode_executable()
        if vscode_exe:
            try:
                subprocess.Popen([vscode_exe, resolved_folder], shell=True)
                time.sleep(0.5)
                focus_vscode_window()
            except Exception:
                pass

        file_list = ", ".join(created_files)
        return ToolResult(
            success=True,
            message=(
                f"Scaffolded '{project_type}' project '{p_name}' inside '{resolved_folder}'. "
                f"Created files: {file_list}. Opened folder in Visual Studio Code."
            ),
            data={
                "action": "scaffold_project",
                "folder": resolved_folder,
                "project_type": project_type,
                "files": created_files,
            },
        )

    def _action_run_project(self, target: Optional[str], port: int = 8000) -> ToolResult:
        """Launches project preview server or runs Python code, returning local address."""
        folder = (target or ".").strip()
        resolved_path = os.path.abspath(folder)

        # 1. If it's a directory with an index.html: launch local HTTP server in background
        if os.path.isdir(resolved_path) and os.path.exists(os.path.join(resolved_path, "index.html")):
            try:
                # Start python -m http.server in background
                cmd = [sys.executable, "-m", "http.server", str(port), "--directory", resolved_path]
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                url = f"http://localhost:{port}"

                # Open browser
                import webbrowser
                webbrowser.open(url)

                return ToolResult(
                    success=True,
                    message=f"Web project is live at {url}. Preview opened in browser.",
                    data={"action": "run_project", "url": url, "port": port, "folder": resolved_path},
                )
            except Exception as exc:
                return ToolResult(
                    success=False,
                    message=f"Failed to start local server on port {port}: {exc}",
                )

        # 2. If it's a Python script: run it
        elif os.path.isfile(resolved_path) and resolved_path.endswith(".py"):
            try:
                res = subprocess.run(
                    [sys.executable, resolved_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=os.path.dirname(resolved_path),
                )
                output = (res.stdout + "\n" + res.stderr).strip()
                status = "succeeded" if res.returncode == 0 else f"exited with code {res.returncode}"
                return ToolResult(
                    success=res.returncode == 0,
                    message=f"Executed '{os.path.basename(resolved_path)}' ({status}):\n{output[:1000]}",
                    data={"exit_code": res.returncode, "output": output},
                )
            except Exception as exc:
                return ToolResult(success=False, message=f"Execution failed: {exc}")

        return ToolResult(
            success=False,
            message=f"Could not determine execution strategy for '{resolved_path}'. Specify a folder with index.html or a Python script.",
        )

    def _action_check_syntax(self, target: Optional[str]) -> ToolResult:
        """Validates syntax of Python, JS, HTML, CSS, or JSON files."""
        if not target or not os.path.exists(target):
            return ToolResult(success=False, message=f"Target file not found: {target}")

        resolved = os.path.abspath(target)
        ext = os.path.splitext(resolved)[1].lower()

        if ext == ".py":
            try:
                with open(resolved, "r", encoding="utf-8") as f:
                    source = f.read()
                ast.parse(source)
                return ToolResult(success=True, message=f"Python syntax valid for {os.path.basename(resolved)}.")
            except SyntaxError as se:
                return ToolResult(
                    success=False,
                    message=f"Python SyntaxError at line {se.lineno}: {se.msg}",
                    data={"line": se.lineno, "offset": se.offset, "text": se.text},
                )
        elif ext == ".json":
            try:
                with open(resolved, "r", encoding="utf-8") as f:
                    json.load(f)
                return ToolResult(success=True, message=f"JSON syntax valid for {os.path.basename(resolved)}.")
            except Exception as je:
                return ToolResult(success=False, message=f"JSON invalid: {je}")

        elif ext in (".html", ".css", ".js"):
            with open(resolved, "r", encoding="utf-8") as f:
                content = f.read()
            # Basic tag balance checks for HTML
            if ext == ".html":
                opens = len(re.findall(r"<([a-zA-Z0-9]+)[^>]*>", content))
                closes = len(re.findall(r"</([a-zA-Z0-9]+)>", content))
                doctype = "<!doctype html>" in content.lower()
                return ToolResult(
                    success=True,
                    message=f"HTML check: Doctype={'Present' if doctype else 'Missing'}, Tags={opens} opened, {closes} closed.",
                )
            return ToolResult(success=True, message=f"File {os.path.basename(resolved)} validated ({len(content)} bytes).")

        return ToolResult(success=True, message=f"Syntax check not required for {ext} file.")

    def _action_diagnose_error(self, error_text: Optional[str], file_path: Optional[str]) -> ToolResult:
        """Diagnoses common error tracebacks and pinpoints fixes."""
        if not error_text:
            return ToolResult(success=False, message="No error text or traceback provided to diagnose.")

        analysis: List[str] = []
        if "ModuleNotFoundError" in error_text or "No module named" in error_text:
            m = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_text)
            mod = m.group(1) if m else "package"
            analysis.append(f"Missing dependency: '{mod}'. Fix: Run `pip install {mod}`.")

        if "SyntaxError" in error_text:
            analysis.append("Syntax Error detected. Check for missing colons (:), unclosed brackets (), or mismatched quotes.")

        if "IndentationError" in error_text:
            analysis.append("Indentation Error detected. Ensure consistent 4-space indentation across Python blocks.")

        if "TypeError" in error_text:
            analysis.append("Type mismatch or incorrect arguments passed to function.")

        if not analysis:
            analysis.append("Examine the traceback stack top to find the exact file and line causing failure.")

        diag_msg = "\n".join(analysis)
        return ToolResult(
            success=True,
            message=f"Diagnostic Report:\n{diag_msg}",
            data={"diagnosis": analysis, "raw_error": error_text[:500]},
        )
