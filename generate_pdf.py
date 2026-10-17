import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and draw total page count and headers/footers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Skip header and footer on cover page
            return
        
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#334155"))
        
        # Running Header
        self.drawString(54, 752, "PROJECT JARVIS • 3-DAY ENGINEERING SPRINT PLAYBOOK")
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawRightString(558, 752, "DAYS 1 — 3 EXECUTION GUIDE")
        
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.6)
        self.line(54, 744, 558, 744)
        
        # Running Footer
        self.line(54, 46, 558, 46)
        self.setFont("Helvetica", 8)
        self.drawString(54, 34, "Project A • Strictly Confidential • For Team Members Jay, Aryan, Abhijit & Rohit")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 34, page_str)
        self.restoreState()

def create_playbook_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=58,
        bottomMargin=54
    )
    
    content_width = 504

    styles = getSampleStyleSheet()
    
    # Custom Color Palette
    PRIMARY = colors.HexColor("#0f172a")     # Deep Slate
    SECONDARY = colors.HexColor("#1e293b")   # Slate
    ACCENT_BLUE = colors.HexColor("#0284c7") # Cyan / Blue
    JAY_COLOR = colors.HexColor("#1e3a8a")   # Dark Navy Blue
    ARYAN_COLOR = colors.HexColor("#0f766e") # Deep Teal
    ABHIJIT_COLOR = colors.HexColor("#c2410c") # Deep Orange / Rust
    ROHIT_COLOR = colors.HexColor("#6b21a8") # Deep Purple
    LIGHT_BG = colors.HexColor("#f8fafc")
    BORDER_COLOR = colors.HexColor("#cbd5e1")
    CODE_BG = colors.HexColor("#f1f5f9")
    PROMPT_BG = colors.HexColor("#eff6ff")
    PROMPT_BORDER = colors.HexColor("#93c5fd")
    GIT_BG = colors.HexColor("#f0fdf4")
    GIT_BORDER = colors.HexColor("#86efac")
    
    # Typography Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=PRIMARY,
        spaceAfter=8
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14
    )
    
    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=SECONDARY,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
        spaceAfter=4
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    code_inline = ParagraphStyle(
        'CodeBlock',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.8,
        leading=10.5,
        textColor=colors.HexColor("#0f172a")
    )
    
    prompt_text = ParagraphStyle(
        'PromptText',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.8,
        leading=10.5,
        textColor=colors.HexColor("#1e3a8a")
    )

    bullet_style = ParagraphStyle(
        'BulletItem',
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )

    story = []

    def make_box(content, bg_color=LIGHT_BG, border_color=BORDER_COLOR, pad=6):
        t = Table([[content]], colWidths=[content_width])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg_color),
            ('BOX', (0,0), (-1,-1), 0.6, border_color),
            ('TOPPADDING', (0,0), (-1,-1), pad),
            ('BOTTOMPADDING', (0,0), (-1,-1), pad),
            ('LEFTPADDING', (0,0), (-1,-1), pad + 2),
            ('RIGHTPADDING', (0,0), (-1,-1), pad + 2),
        ]))
        return t

    def make_prompt_box(title: str, prompt_str: str):
        content = [
            Paragraph(f"<b>📋 EXACT ANTIGRAVITY PROMPT: {title}</b>", ParagraphStyle('PT', parent=body_bold, textColor=colors.HexColor("#1e40af"), fontSize=8, leading=11, spaceAfter=3)),
            Paragraph(prompt_str.replace("\n", "<br/>").replace(" ", "&nbsp;"), prompt_text)
        ]
        t = Table([[content]], colWidths=[content_width])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), PROMPT_BG),
            ('BOX', (0,0), (-1,-1), 0.75, PROMPT_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
        ]))
        return t

    def make_git_box(cmd_str: str):
        content = [
            Paragraph("<b>⚡ GIT COMMANDS (RUN IN TERMINAL):</b>", ParagraphStyle('GT', parent=body_bold, textColor=colors.HexColor("#166534"), fontSize=7.8, leading=10, spaceAfter=2)),
            Paragraph(cmd_str.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_inline)
        ]
        t = Table([[content]], colWidths=[content_width])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), GIT_BG),
            ('BOX', (0,0), (-1,-1), 0.75, GIT_BORDER),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
        ]))
        return t

    def make_day_card(role_color, day_title, goal, steps, prompt_title, prompt, git_cmd, verify_test):
        elements = []
        elements.append(Paragraph(f"<font color='{role_color.hexval()}'><b>{day_title}</b></font>", h2_style))
        elements.append(Paragraph(f"<b>Today's Goal:</b> {goal}", body_style))
        elements.append(Paragraph("<b>How to Do It (Step-by-Step):</b><br/>" + steps, body_style))
        elements.append(Spacer(1, 2))
        elements.append(make_prompt_box(prompt_title, prompt))
        elements.append(Spacer(1, 2))
        elements.append(make_git_box(git_cmd))
        elements.append(Spacer(1, 2))
        elements.append(Paragraph(f"<b>Acceptance Test & Expected Output:</b> {verify_test}", ParagraphStyle('VT', parent=body_style, textColor=colors.HexColor("#0f172a"))))
        elements.append(Spacer(1, 4))
        return KeepTogether(elements)

    # =========================================================================
    # PAGE 1: COVER & EXECUTIVE SUMMARY
    # =========================================================================
    story.append(Spacer(1, 10))
    story.append(Paragraph("PROJECT JARVIS • TACTICAL ENGINEERING MANUAL", ParagraphStyle('MetaH', fontName='Helvetica-Bold', fontSize=9.5, textColor=ACCENT_BLUE, leading=13, spaceAfter=5)))
    story.append(Paragraph("3-Day Deep-Dive Execution Playbook", title_style))
    story.append(Paragraph("A zero-to-one guide for 4 engineers building an autonomous desktop AI assistant with Antigravity", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceBefore=2, spaceAfter=10))

    meta_table = Table([
        [
            Paragraph("<b>Sprint Timeline:</b> Days 1 to 3 (Starting Tomorrow)", body_style),
            Paragraph("<b>Target Stack:</b> Python 3.11, Antigravity, FastAPI, Gemini API", body_style)
        ],
        [
            Paragraph("<b>Target Deliverable:</b> Working ReAct Desktop Agent MVP", body_style),
            Paragraph("<b>Governance Model:</b> Modular Isolation & Git Feature Branches", body_style)
        ]
    ], colWidths=[240, 264])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    role_summary_data = [
        [Paragraph("<b>Role & Engineer</b>", body_bold), Paragraph("<b>Folder Territory</b>", body_bold), Paragraph("<b>3-Day Focus & Deliverables</b>", body_bold)],
        [
            Paragraph("<font color='#1e3a8a'><b>Jay</b><br/>Lead & Core Brain</font>", body_style),
            Paragraph("<code>core/</code><br/><i>(Only Jay edits)</i>", code_inline),
            Paragraph("Repository initialization, LLM connectivity (Gemini API), multi-turn conversation memory, and autonomous function-calling (ReAct) execution loop.", body_style)
        ],
        [
            Paragraph("<font color='#0f766e'><b>Aryan</b><br/>Voice Engineer</font>", body_style),
            Paragraph("<code>voice/</code><br/><i>(Only Aryan edits)</i>", code_inline),
            Paragraph("Audio hardware validation (16kHz mono), Speech-to-Text (STT) transcription pipeline, and low-latency Neural Text-to-Speech (TTS) synthesis.", body_style)
        ],
        [
            Paragraph("<font color='#c2410c'><b>Abhijit</b><br/>System & Automation</font>", body_style),
            Paragraph("<code>tools/</code><br/><i>(Only Abhijit edits)</i>", code_inline),
            Paragraph("OS telemetry tools (CPU, RAM, battery), asynchronous application launcher, sandboxed file operations, and security confirmation guardrails.", body_style)
        ],
        [
            Paragraph("<font color='#6b21a8'><b>Rohit</b><br/>Frontend & Memory</font>", body_style),
            Paragraph("<code>memory/</code> & <code>ui/</code><br/><i>(Only Rohit edits)</i>", code_inline),
            Paragraph("FastAPI backend server, persistent SQLite notes and interaction logs, real-time WebSocket bridge, and sci-fi dark mode HUD chat interface.", body_style)
        ]
    ]
    role_table = Table(role_summary_data, colWidths=[120, 94, 290])
    role_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(role_table)
    story.append(Spacer(1, 10))

    exec_text = (
        "<b>The Learning & Engineering Philosophy:</b> You are using Antigravity as an accelerator, not a magic crutch. "
        "Every engineer must understand their code line-by-line. Never accept generated code you cannot explain in a technical viva "
        "or interview. To avoid merge disasters, everyone adheres strictly to their assigned module directory. If you need a function "
        "from another module, request that teammate to expose an interface—<b>never edit their folder directly</b>."
    )
    story.append(make_box(Paragraph(exec_text, body_style), bg_color=colors.HexColor("#f8fafc"), border_color=ACCENT_BLUE, pad=6))
    
    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 1: PART 1 — GIT CONFIG, REPO SETUP & VIRTUAL ENVIRONMENT (PAGE 2)
    # =========================================================================
    story.append(Paragraph("CHAPTER 1: UNIVERSAL SETUP & GIT PROTOCOL", h1_style))
    story.append(Paragraph("Every teammate must follow this setup sequentially before beginning Day 1 tasks.", body_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("1.1 Git & GitHub Configuration (Everyone)", h2_style))
    story.append(Paragraph("1. <b>Create Account:</b> Sign up at <font color='#0284c7'>github.com</font> if you do not have an account.<br/>"
                           "2. <b>Install Git:</b> Download and install <i>Git for Windows</i> from git-scm.com. Ensure <b>Git Credential Manager</b> is checked.<br/>"
                           "3. <b>Configure Identity:</b> Run in your PowerShell:", body_style))
    story.append(make_box(Paragraph("git config --global user.name \"Your Full Name\"<br/>git config --global user.email \"your_email@example.com\"", code_inline), bg_color=CODE_BG, pad=4))
    
    story.append(Paragraph("1.2 Repository Setup & Branching Strategy", h2_style))
    story.append(Paragraph(
        "• <b>Jay</b> initializes the repository on GitHub (<code>jarvis-desktop-assistant</code>) and invites Aryan, Abhijit, and Rohit as collaborators.<br/>"
        "• <b>Aryan, Abhijit, and Rohit</b> accept the GitHub email/notification invite, then clone the repository onto their laptops:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>git clone https://github.com/JAY_USERNAME/jarvis-desktop-assistant.git</code><br/>"
        "• <b>Branching Rule:</b> NEVER commit directly to <code>main</code>. Each developer works in a dedicated branch:",
        body_style
    ))
    story.append(make_box(Paragraph(
        "# Jay's branch:<br/>git checkout -b feature/jay-core<br/><br/>"
        "# Aryan's branch:<br/>git checkout -b feature/aryan-voice<br/><br/>"
        "# Abhijit's branch:<br/>git checkout -b feature/abhijit-tools<br/><br/>"
        "# Rohit's branch:<br/>git checkout -b feature/rohit-ui-memory",
        code_inline
    ), bg_color=CODE_BG, pad=4))

    story.append(Paragraph("1.3 Virtual Environment & Secrets Protection", h2_style))
    story.append(Paragraph(
        "Run these commands in PowerShell in the project root: <br/>"
        "1. <code>python -m venv venv</code><br/>"
        "2. <code>.\\venv\\Scripts\\Activate.ps1</code> (If permission error: <code>Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass</code>)<br/>"
        "3. <code>pip install -r requirements.txt</code><br/>"
        "4. <code>cp .env.example .env</code> (Add your API key inside <code>.env</code>. <b>NEVER COMMIT .ENV!</b>)",
        body_style
    ))

    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 1: PART 2 — ANTIGRAVITY PROMPTING & DAILY CADENCE (PAGE 3)
    # =========================================================================
    story.append(Paragraph("1.4 How to Open and Prompt Antigravity Correctly", h1_style))
    story.append(Paragraph(
        "⚠️ <b>WHICH FOLDER TO OPEN:</b> Open the <b>ROOT project folder</b> (<code>Project - A</code>) in Antigravity. "
        "<b>NEVER</b> open a single subfolder (like <code>voice/</code>) alone, because Antigravity will lose sight of "
        "<code>ARCHITECTURE.md</code>, <code>AGENTS.md</code>, <code>requirements.txt</code>, and root Python imports.",
        body_style
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("<b>The Golden Antigravity Prompting Rule:</b> Every prompt must start with your identity and territory constraint:", body_style))
    story.append(make_box(Paragraph(
        "<i>\"I am [Your Name], the [Your Role] for Project Jarvis. You are ONLY allowed to create or edit files inside the [your_folder]/ directory. "
        "Do not touch any other folder, ARCHITECTURE.md, or .env. Use Python 3.11 with strict type hints and docstrings. Wrap all logic in try/except "
        "and provide a runnable verification test script.\"</i>",
        body_style
    ), bg_color=PROMPT_BG, border_color=PROMPT_BORDER, pad=6))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1.5 The End-of-Day Git Cadence (Push & Pull Request)", h2_style))
    story.append(Paragraph("At the end of each day or feature, stage only your folder, commit, and push to GitHub:", body_style))
    story.append(make_box(Paragraph(
        "git status                              # Verify .env is NOT listed under untracked files!<br/>"
        "git add [your_folder]/                  # e.g., git add voice/<br/>"
        "git commit -m \"feat: implement day X milestone\"<br/>"
        "git push -u origin feature/[your-branch]<br/>"
        "# Then open GitHub in browser and click 'Compare & Pull Request' targeting main",
        code_inline
    ), bg_color=GIT_BG, border_color=GIT_BORDER, pad=5))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1.6 How to Sync Latest Merged Code From Main", h2_style))
    story.append(Paragraph("Whenever Jay merges a pull request on GitHub, update your local branch cleanly without conflicts:", body_style))
    story.append(make_box(Paragraph(
        "# Step 1: Switch to local main and pull newest commits<br/>"
        "git checkout main<br/>"
        "git pull origin main<br/><br/>"
        "# Step 2: Switch back to your feature branch and merge main into it<br/>"
        "git checkout feature/[your-branch]<br/>"
        "git merge main",
        code_inline
    ), bg_color=CODE_BG, pad=5))

    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 2: JAY — TEAM LEAD & CORE BRAIN (PAGES 4-5)
    # =========================================================================
    story.append(Paragraph("CHAPTER 2: JAY • TEAM LEAD & CORE BRAIN", h1_style))
    story.append(Paragraph("<b>Ownership Territory:</b> <code>core/</code>, <code>ARCHITECTURE.md</code>, central runners (<code>main_cli.py</code>), merging PRs.", body_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=JAY_COLOR, spaceBefore=2, spaceAfter=8))

    # Jay Day 1
    story.append(make_day_card(
        JAY_COLOR,
        "■ Day 1: Central Repository Initialization & LLM API Connectivity",
        "Launch the central GitHub repo, invite teammates, establish contracts, and verify LLM API calls in Python.",
        "1. Run <code>git init</code>, set remote, push initial commit with ARCHITECTURE.md, AGENTS.md, .gitignore.<br/>"
        "2. Add Aryan, Abhijit, and Rohit as collaborators on GitHub.<br/>"
        "3. Obtain Gemini API key from Google AI Studio. Add to <code>.env</code> as <code>GEMINI_API_KEY</code>.<br/>"
        "4. Create <code>core/test_llm.py</code> using <code>google-genai</code> to call <code>gemini-2.5-flash</code>.",
        "Jay Day 1 — LLM Sanity Check",
        "I am Jay, Lead of Project Jarvis. You may ONLY create and edit files inside core/.\n"
        "Read .env to retrieve GEMINI_API_KEY using python-dotenv. Use the google-genai SDK.\n"
        "Create core/test_llm.py that initializes the Gemini client with model 'gemini-2.5-flash'.\n"
        "Send a prompt: 'Hello, confirm your identity as Jarvis Core.'\n"
        "Print the response with elapsed latency in seconds. Handle missing API key exceptions cleanly.\n"
        "Include strict type hints and docstrings.",
        "git checkout -b feature/jay-core\n"
        "git add core/test_llm.py\n"
        "git commit -m \"feat(core): initialize LLM test runner with gemini-2.5-flash\"\n"
        "git push -u origin feature/jay-core",
        "Run <code>python core/test_llm.py</code>. Terminal prints: <i>\"Jarvis core initialized successfully. Latency: 0.42s\"</i>."
    ))

    # Jay Day 2
    story.append(make_day_card(
        JAY_COLOR,
        "■ Day 2: Multi-Turn Conversation Memory & System Prompt Persona",
        "Build <code>core/brain.py</code> with multi-turn conversation memory and system prompt persona.",
        "1. Create class <code>JarvisBrain</code> in <code>core/brain.py</code>.<br/>"
        "2. Configure System Prompt: Concise, witty, tech-savvy assistant designed for desktop automation.<br/>"
        "3. Implement <code>chat(user_message: str) -> str</code> maintaining a message history buffer.<br/>"
        "4. Build <code>main_cli.py</code> at project root to run an interactive terminal chat session.",
        "Jay Day 2 — Conversational Brain & CLI Loop",
        "I am Jay. You may ONLY modify files in core/ and main_cli.py.\n"
        "Implement JarvisBrain in core/brain.py:\n"
        "1. Load GEMINI_API_KEY from .env.\n"
        "2. Define system prompt: 'You are Jarvis, an ultra-efficient desktop assistant. Speak concisely in 1-2 sentences suitable for voice.'\n"
        "3. Maintain conversation history list. Add chat(message: str) -> str method.\n"
        "4. Create main_cli.py with an interactive while loop: user inputs prompt, Jarvis responds. Type 'exit' to quit.",
        "git add core/brain.py main_cli.py\n"
        "git commit -m \"feat(core): implement multi-turn chat memory and terminal CLI loop\"\n"
        "git push origin feature/jay-core",
        "Run <code>python main_cli.py</code>. Tell it: <i>\"My name is Jay\"</i>, then ask <i>\"What is my name?\"</i>. Jarvis replies: <i>\"Your name is Jay.\"</i>."
    ))

    # Jay Day 3
    story.append(make_day_card(
        JAY_COLOR,
        "■ Day 3: Autonomous Function-Calling (ReAct) Tool Execution Engine",
        "Enable the Brain to dynamically inspect Abhijit's tool schemas, execute them, and interpret results.",
        "1. Import <code>tools.registry</code> into <code>core/brain.py</code>.<br/>"
        "2. Convert tool schemas into Gemini Function Declarations.<br/>"
        "3. When the LLM emits a tool call, extract name and arguments.<br/>"
        "4. Call <code>tools.registry.execute_tool(name, args)</code>, capture <code>ToolResult</code>, and feed it back to Gemini for the final natural language response.",
        "Jay Day 3 — ReAct Function Calling Loop",
        "I am Jay. You may ONLY modify files inside core/.\n"
        "Integrate Abhijit's tools from tools.registry into the Gemini function calling flow in core/brain.py:\n"
        "1. Retrieve registered tools and convert their get_schema() into Gemini Tool declarations.\n"
        "2. When sending messages, pass tools=tools.\n"
        "3. If model responds with function_calls, iterate over calls, execute via tools.registry.execute_tool(name, args), and return ToolResult.to_llm_string().\n"
        "4. Send tool output back to Gemini so it summarizes the result to the user.",
        "git add core/brain.py tests/test_brain.py\n"
        "git commit -m \"feat(core): implement ReAct tool-calling loop for autonomous execution\"\n"
        "git push origin feature/jay-core",
        "In <code>main_cli.py</code>, type: <i>\"Check my RAM and open Notepad\"</i>. Notepad pops up, and Jarvis replies: <i>\"I've opened Notepad, and your RAM usage is 42%.\"</i>."
    ))

    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 3: ARYAN — VOICE ENGINEER (PAGES 6-7)
    # =========================================================================
    story.append(Paragraph("CHAPTER 3: ARYAN • VOICE ENGINEER", h1_style))
    story.append(Paragraph("<b>Ownership Territory:</b> <code>voice/</code>, microphone capture, STT, and neural TTS voice streaming.", body_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ARYAN_COLOR, spaceBefore=2, spaceAfter=8))

    # Aryan Day 1
    story.append(make_day_card(
        ARYAN_COLOR,
        "■ Day 1: Audio Hardware Diagnostics & Sampling Verification",
        "Verify laptop microphone input and speaker output using Python <code>sounddevice</code> and <code>numpy</code>.",
        "1. Checkout branch: <code>git checkout -b feature/aryan-voice</code>.<br/>"
        "2. Install packages: <code>pip install sounddevice numpy soundfile</code>.<br/>"
        "3. Create <code>voice/audio_check.py</code> to list audio devices and perform a 3-second recording and playback test.",
        "Aryan Day 1 — Audio Diagnostics",
        "I am Aryan, Voice Engineer for Project Jarvis. You may ONLY modify files inside voice/.\n"
        "Create voice/audio_check.py using sounddevice, soundfile, and numpy:\n"
        "1. Query and list all audio host APIs and default input/output devices.\n"
        "2. Record 3 seconds of audio from the default microphone at 16000 Hz, mono channel, 16-bit PCM.\n"
        "3. Save the recording to temp_audio/mic_test.wav (create folder if missing).\n"
        "4. Play the recorded audio back through default speakers.\n"
        "5. Include clear error handling if mic permissions are denied.",
        "git checkout -b feature/aryan-voice\n"
        "git add voice/audio_check.py\n"
        "git commit -m \"feat(voice): implement 16kHz audio recording and playback check\"\n"
        "git push -u origin feature/aryan-voice",
        "Run <code>python voice/audio_check.py</code>. Speak during the 3 seconds; your voice plays back clearly through laptop speakers."
    ))

    # Aryan Day 2
    story.append(make_day_card(
        ARYAN_COLOR,
        "■ Day 2: Speech-to-Text (STT) Transcription Pipeline",
        "Build <code>voice/stt.py</code> to capture spoken commands and transcribe them into clean text.",
        "1. Select STT engine: <code>faster-whisper</code> (offline CPU) or Groq Whisper API (instant cloud).<br/>"
        "2. Implement <code>Transcriber</code> class with <code>transcribe_mic(duration=4) -> str</code>.<br/>"
        "3. Build <code>voice/test_stt.py</code> to verify accuracy on speech.",
        "Aryan Day 2 — STT Transcriber",
        "I am Aryan. You may ONLY modify files inside voice/.\n"
        "Create voice/stt.py implementing a Speech-to-Text transcriber.\n"
        "Use faster-whisper (tiny or base model) for local transcription.\n"
        "Signature: transcribe_mic(duration_seconds: int = 4) -> str.\n"
        "1. Record audio at 16kHz mono.\n"
        "2. Run Whisper model inference on audio buffer.\n"
        "3. Return normalized, stripped text string.\n"
        "Create voice/test_stt.py: prompts 'Speak now...', records, and prints 'Transcript: [your text]'.",
        "git add voice/stt.py voice/test_stt.py\n"
        "git commit -m \"feat(voice): implement speech-to-text pipeline using whisper\"\n"
        "git push origin feature/aryan-voice",
        "Run <code>python voice/test_stt.py</code>. Say: <i>\"Jarvis what is the date today?\"</i>. Terminal outputs matching text with >90% accuracy."
    ))

    # Aryan Day 3
    story.append(make_day_card(
        ARYAN_COLOR,
        "■ Day 3: Neural Text-to-Speech (TTS) Voice Engine",
        "Implement high-fidelity neural speech generation so Jarvis can speak back naturally.",
        "1. Install <code>edge-tts</code> and <code>pygame</code> (or <code>playsound3</code>).<br/>"
        "2. Create <code>voice/tts.py</code> with <code>JarvisSpeaker</code> class.<br/>"
        "3. Configure voice model: <code>en-US-GuyNeural</code>.<br/>"
        "4. Implement <code>speak(text: str)</code> with non-blocking audio playback.",
        "Aryan Day 3 — Neural TTS Synthesis",
        "I am Aryan. You may ONLY modify files inside voice/.\n"
        "Create voice/tts.py using edge-tts and sounddevice/playsound3.\n"
        "1. Define JarvisSpeaker with default voice 'en-US-GuyNeural'.\n"
        "2. Method async def speak_async(text: str): stream audio from edge-tts to temp_audio/speech.mp3 and play it.\n"
        "3. Method def speak(text: str): synchronous helper for easy calling.\n"
        "4. Handle empty strings, special characters, and audio driver busy locks gracefully.\n"
        "Create voice/test_tts.py that speaks: 'Good evening Jay. All systems are operational.'",
        "git add voice/tts.py voice/test_tts.py\n"
        "git commit -m \"feat(voice): implement edge-tts neural voice generation engine\"\n"
        "git push origin feature/aryan-voice",
        "Run <code>python voice/test_tts.py</code>. Laptop speakers speak the phrase in a crisp, natural human voice in under 1 second."
    ))

    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 4: ABHIJIT — SYSTEM & AUTOMATION ENGINEER (PAGES 8-9)
    # =========================================================================
    story.append(Paragraph("CHAPTER 4: ABHIJIT • SYSTEM & AUTOMATION ENGINEER", h1_style))
    story.append(Paragraph("<b>Ownership Territory:</b> <code>tools/</code>, OS automation, app launching, file sandboxing, safety guardrails.", body_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ABHIJIT_COLOR, spaceBefore=2, spaceAfter=8))

    # Abhijit Day 1
    story.append(make_day_card(
        ABHIJIT_COLOR,
        "■ Day 1: OS Telemetry & Asynchronous Process Spawning",
        "Build raw OS telemetry probes and verify asynchronous application launching on Windows.",
        "1. Checkout branch: <code>git checkout -b feature/abhijit-tools</code>.<br/>"
        "2. Review <code>tools/base.py</code> to internalize <code>BaseTool</code> and <code>ToolResult</code>.<br/>"
        "3. Install packages: <code>pip install psutil pyautogui pillow</code>.<br/>"
        "4. Create <code>tools/test_system.py</code> to test CPU, RAM, battery sensors and non-blocking <code>subprocess.Popen</code>.",
        "Abhijit Day 1 — OS Telemetry & Process Spawning",
        "I am Abhijit, System Engineer for Project Jarvis. You may ONLY modify files inside tools/.\n"
        "Study tools/base.py. Never modify tools/base.py or ARCHITECTURE.md.\n"
        "Create tools/test_system.py using psutil and subprocess:\n"
        "1. Extract CPU % (interval=0.2), used and total RAM in GB, and battery percentage + plugged status.\n"
        "2. Launch notepad.exe using subprocess.Popen (ensure non-blocking, so python script continues immediately).\n"
        "3. Print telemetry in structured JSON.\n"
        "4. Ensure it runs cleanly on Windows 10/11.",
        "git checkout -b feature/abhijit-tools\n"
        "git add tools/test_system.py\n"
        "git commit -m \"feat(tools): implement system telemetry probe and non-blocking app launch\"\n"
        "git push -u origin feature/abhijit-tools",
        "Run <code>python tools/test_system.py</code>. Notepad opens immediately, and CPU/RAM JSON stats print in terminal."
    ))

    # Abhijit Day 2
    story.append(make_day_card(
        ABHIJIT_COLOR,
        "■ Day 2: Standardized System Tools & Central Tool Registry",
        "Implement core tools adhering to <code>BaseTool</code> and construct <code>tools/registry.py</code>.",
        "1. Implement <code>GetSystemStatsTool</code>, <code>OpenAppTool</code>, and <code>ListDirectoryTool</code> in <code>tools/system_tools.py</code>.<br/>"
        "2. Build <code>tools/registry.py</code>: Dictionary registering tools by name.<br/>"
        "3. Implement <code>execute_tool(name: str, args: dict) -> ToolResult</code> with robust exception handling.",
        "Abhijit Day 2 — System Tools & Registry",
        "I am Abhijit. You may ONLY modify files inside tools/.\n"
        "Implement the following tools inheriting from BaseTool in tools/base.py:\n"
        "1. OpenAppTool in tools/system_tools.py: takes app_name: str. Maps shortcuts ('chrome', 'code', 'calc', 'notepad', 'spotify') to Windows executable paths. Returns ToolResult.\n"
        "2. ListDirectoryTool in tools/system_tools.py: takes directory_path: str (defaults to '.'). Returns list of files/folders.\n"
        "3. Create tools/registry.py: dictionary registering GetSystemStatsTool, OpenAppTool, and ListDirectoryTool. Function execute_tool(name: str, args: dict) -> ToolResult that executes safely and catches unknown tool errors.\n"
        "Include get_schema() returning valid JSON schemas for LLM tool calling.",
        "git add tools/system_tools.py tools/registry.py\n"
        "git commit -m \"feat(tools): implement standardized system tools and central execution registry\"\n"
        "git push origin feature/abhijit-tools",
        "Run <code>python -c \"from tools.registry import execute_tool; print(execute_tool('open_app', {'app_name': 'calc'}))\"</code>. Calculator opens and ToolResult prints <code>success=True</code>."
    ))

    # Abhijit Day 3
    story.append(make_day_card(
        ABHIJIT_COLOR,
        "■ Day 3: Sandboxed File Operations & Safety Guardrail Engine",
        "Create safe file reading/writing tools with sandbox guardrails preventing accidental data destruction.",
        "1. Create <code>tools/safety.py</code>: Restrict file operations to safe folders; block root system paths (<code>C:\\Windows</code>, <code>C:\\Program Files</code>).<br/>"
        "2. Create <code>tools/file_tools.py</code>: <code>ReadFileTool</code>, <code>WriteFileTool</code>.<br/>"
        "3. Implement overwrite confirmation: if a file exists and <code>overwrite=False</code>, require confirmation.",
        "Abhijit Day 3 — Sandboxed File Tools & Safety Guards",
        "I am Abhijit. You may ONLY modify files inside tools/.\n"
        "1. Create tools/safety.py with is_path_safe(path: str) -> bool. Disallow paths inside Windows system directories and enforce sandbox restrictions.\n"
        "2. In tools/file_tools.py, implement ReadFileTool(file_path: str) -> ToolResult.\n"
        "3. In tools/file_tools.py, implement WriteFileTool(file_path: str, content: str, overwrite: bool = False) -> ToolResult. If file exists and overwrite is False, return success=False asking for confirmation.\n"
        "4. Register both in tools/registry.py.\n"
        "Write unit tests in tests/test_tools.py checking both successful writes and blocked dangerous paths.",
        "git add tools/file_tools.py tools/safety.py tests/test_tools.py\n"
        "git commit -m \"feat(tools): implement sandboxed file tools and safety guardrail engine\"\n"
        "git push origin feature/abhijit-tools",
        "Run <code>pytest tests/test_tools.py</code>. Sandbox file write succeeds; writing into <code>C:\\Windows\\System32</code> returns Permission Denied."
    ))

    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 5: ROHIT — FRONTEND & MEMORY ENGINEER (PAGES 10-11)
    # =========================================================================
    story.append(Paragraph("CHAPTER 5: ROHIT • FRONTEND & MEMORY ENGINEER", h1_style))
    story.append(Paragraph("<b>Ownership Territory:</b> <code>memory/</code>, <code>ui/</code>, SQLite database, FastAPI REST/WebSocket server, Web HUD.", body_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ROHIT_COLOR, spaceBefore=2, spaceAfter=8))

    # Rohit Day 1
    story.append(make_day_card(
        ROHIT_COLOR,
        "■ Day 1: FastAPI Backend Setup & Persistent SQLite Database",
        "Set up the backend server and initialize the SQLite schema for persistent notes and interaction logs.",
        "1. Checkout branch: <code>git checkout -b feature/rohit-ui-memory</code>.<br/>"
        "2. Install packages: <code>pip install fastapi uvicorn[standard] aiosqlite websockets</code>.<br/>"
        "3. Create <code>memory/db.py</code> to initialize <code>memory/jarvis.db</code> with tables: <code>notes</code> and <code>chat_history</code>.<br/>"
        "4. Create <code>ui/server.py</code> with FastAPI application and healthcheck endpoint.",
        "Rohit Day 1 — Backend & SQLite Database",
        "I am Rohit, Frontend & Memory Engineer for Project Jarvis. You may ONLY modify memory/ and ui/.\n"
        "1. In memory/db.py, write async functions to initialize memory/jarvis.db with aiosqlite:\n"
        "   - Table notes: id INTEGER PRIMARY KEY, title TEXT, content TEXT, created_at TIMESTAMP\n"
        "   - Table chat_history: id INTEGER PRIMARY KEY, role TEXT, content TEXT, timestamp TIMESTAMP\n"
        "   - Enable WAL mode (PRAGMA journal_mode=WAL) for high performance.\n"
        "2. In ui/server.py, create a FastAPI app. Include an @app.on_event('startup') handler that calls db initialization.\n"
        "3. Add GET /health returning {'status': 'healthy', 'db': 'connected'}.\n"
        "Include unit test in tests/test_memory.py.",
        "git checkout -b feature/rohit-ui-memory\n"
        "git add memory/db.py ui/server.py tests/test_memory.py\n"
        "git commit -m \"feat(backend): initialize FastAPI server and SQLite persistent store\"\n"
        "git push -u origin feature/rohit-ui-memory",
        "Run <code>uvicorn ui.server:app --reload</code>. Visit <code>http://127.0.0.1:8000/health</code>. JSON returns: <code>{\"status\": \"healthy\"}</code>."
    ))

    # Rohit Day 2
    story.append(make_day_card(
        ROHIT_COLOR,
        "■ Day 2: Note Taking CRUD & REST API Endpoints",
        "Build full CRUD operations for long-term memory notes and expose REST endpoints for the assistant.",
        "1. Create <code>memory/storage.py</code>: <code>create_note(title, content)</code>, <code>get_notes()</code>, <code>search_notes(keyword)</code>.<br/>"
        "2. Expose in <code>ui/server.py</code>: <code>POST /api/notes</code> (Pydantic validated) and <code>GET /api/notes</code>.<br/>"
        "3. Add endpoint <code>GET /api/telemetry</code> calling Abhijit's <code>GetSystemStatsTool</code> to verify module interop.",
        "Rohit Day 2 — Memory Manager & REST APIs",
        "I am Rohit. You may ONLY modify memory/ and ui/.\n"
        "1. Create memory/storage.py with class MemoryManager:\n"
        "   - async add_note(title: str, content: str) -> int\n"
        "   - async list_notes(limit: int = 20) -> list[dict]\n"
        "   - async search_notes(query: str) -> list[dict]\n"
        "2. In ui/server.py, define Pydantic schema NoteCreate(title: str, content: str).\n"
        "3. Add POST /api/notes (creates note) and GET /api/notes (retrieves notes).\n"
        "4. Add GET /api/telemetry which calls tools.system_tools.GetSystemStatsTool().run() to display live system stats on API.",
        "git add memory/storage.py ui/server.py\n"
        "git commit -m \"feat(memory): implement note taking CRUD and REST API endpoints\"\n"
        "git push origin feature/rohit-ui-memory",
        "Open <code>http://127.0.0.1:8000/docs</code>. Use interactive Swagger UI to POST note 'Buy Groceries'. Verify it returns 201 Created and persists in SQLite."
    ))

    # Rohit Day 3
    story.append(make_day_card(
        ROHIT_COLOR,
        "■ Day 3: WebSocket Live Channel & Sci-Fi Web HUD Client",
        "Build the real-time WebSocket channel and a sleek dark-mode Jarvis HUD chat interface.",
        "1. Add WebSocket route <code>@app.websocket('/ws/jarvis')</code> in <code>ui/server.py</code>.<br/>"
        "2. Build single-page web client <code>ui/index.html</code> styled with dark sci-fi aesthetic (`#0f172a`, cyan glowing borders, monospace font).<br/>"
        "3. Implement live message exchange: user sends prompt -> UI displays 'Thinking...' badge -> receives streamed chunks or tool status.",
        "Rohit Day 3 — WebSockets & Sci-Fi HUD Client",
        "I am Rohit. You may ONLY modify memory/ and ui/.\n"
        "1. In ui/server.py, add @app.websocket('/ws/jarvis'). Handle incoming JSON: {'action': 'chat', 'text': str}.\n"
        "2. Push progress events: {'type': 'status', 'status': 'thinking'}, then {'type': 'response', 'text': str}.\n"
        "3. Create ui/index.html with a futuristic Jarvis HUD interface:\n"
        "   - Dark slate theme (#0f172a), cyan glowing accents, telemetry widget showing CPU/RAM.\n"
        "   - Message feed displaying user and assistant chat bubbles.\n"
        "   - Status indicator (Idle, Listening, Thinking, Executing Tool).\n"
        "4. Mount ui/ static directory in server.py so visiting http://127.0.0.1:8000 serves the HUD.",
        "git add ui/server.py ui/index.html\n"
        "git commit -m \"feat(ui): implement real-time WebSocket channel and futuristic web HUD\"\n"
        "git push origin feature/rohit-ui-memory",
        "Open <code>http://127.0.0.1:8000</code> in browser. Type a message in the HUD. The UI connects over WebSocket and displays real-time responses."
    ))

    story.append(PageBreak())

    # =========================================================================
    # CHAPTER 6: INTEGRATION CHECKPOINT (DAY 4 PREVIEW) (PAGE 12)
    # =========================================================================
    story.append(Paragraph("CHAPTER 6: DAY 4 INTEGRATION PREVIEW", h1_style))
    story.append(Paragraph("How the 4 modules lock together into a single functioning desktop assistant.", body_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("6.1 The 5-Step Integration Pipeline", h2_style))
    dataflow_steps = [
        [Paragraph("<b>Step</b>", body_bold), Paragraph("<b>Module Owner</b>", body_bold), Paragraph("<b>Action & Interface Contract</b>", body_bold)],
        [
            Paragraph("1. Input", body_bold),
            Paragraph("Aryan (<code>voice/</code>) or Rohit (<code>ui/</code>)", body_style),
            Paragraph("Captures spoken voice via STT or typed command via WebSocket HUD; passes text string to Jay's Brain.", body_style)
        ],
        [
            Paragraph("2. Decision", body_bold),
            Paragraph("Jay (<code>core/</code>)", body_style),
            Paragraph("LLM evaluates prompt with memory context; determines whether to answer directly or invoke a registered tool.", body_style)
        ],
        [
            Paragraph("3. Execution", body_bold),
            Paragraph("Abhijit (<code>tools/</code>)", body_style),
            Paragraph("Tool registry executes OS command, app launch, or file operation; returns structured <code>ToolResult</code>.", body_style)
        ],
        [
            Paragraph("4. Storage", body_bold),
            Paragraph("Rohit (<code>memory/</code>)", body_style),
            Paragraph("Conversation turns and new user notes are saved into SQLite database.", body_style)
        ],
        [
            Paragraph("5. Output", body_bold),
            Paragraph("Aryan (<code>voice/</code>) & Rohit (<code>ui/</code>)", body_style),
            Paragraph("TTS synthesizes voice reply through speakers; WebSocket pushes live text and status update to HUD.", body_style)
        ]
    ]
    df_table = Table(dataflow_steps, colWidths=[64, 140, 300])
    df_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(df_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("6.2 Daily Standup Meeting Agenda (15 Minutes Every Evening)", h2_style))
    story.append(Paragraph("Hold a 15-minute voice call every evening at 8:00 PM. Each person answers strictly 3 questions:", body_style))
    story.append(Paragraph("1. <b>What did I build and verify today?</b> (Share screen for 1 minute showing your code running).", bullet_style))
    story.append(Paragraph("2. <b>What technical blocker or error did I encounter?</b> (Discuss unexpected bugs or API issues).", bullet_style))
    story.append(Paragraph("3. <b>Is my branch clean and pushed to GitHub for PR review?</b> (Jay confirms review status).", bullet_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("6.3 Master Troubleshooting & Antigravity Gotchas", h2_style))
    trouble_data = [
        [Paragraph("<b>Issue / Error</b>", body_bold), Paragraph("<b>Root Cause</b>", body_bold), Paragraph("<b>How to Fix It</b>", body_bold)],
        [
            Paragraph("PowerShell script execution disabled", body_style),
            Paragraph("Windows ExecutionPolicy security restriction", body_style),
            Paragraph("Run: <code>Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass</code>", code_inline)
        ],
        [
            Paragraph("Antigravity edits other people's folders", body_style),
            Paragraph("Prompt didn't enforce boundary rule", body_style),
            Paragraph("Prepend: <i>'You are ONLY allowed to edit files in [module]/'</i> to every prompt.", body_style)
        ],
        [
            Paragraph("Audio device busy / crash", body_style),
            Paragraph("Multiple processes holding microphone stream", body_style),
            Paragraph("Close other recording apps; use context manager <code>with sd.InputStream()</code>", body_style)
        ],
        [
            Paragraph("FastAPI freezes on tool call", body_style),
            Paragraph("Synchronous blocking call inside async route", body_style),
            Paragraph("Wrap execution with <code>asyncio.to_thread(execute_tool, ...)</code>", code_inline)
        ]
    ]
    tb_table = Table(trouble_data, colWidths=[120, 144, 240])
    tb_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('INNERGRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(tb_table)
    
    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully compiled at: {output_path}")

if __name__ == "__main__":
    out_pdf = r"d:\engineers\Project - A\JARVIS_3_DAY_SPRINT_PLAYBOOK.pdf"
    create_playbook_pdf(out_pdf)
