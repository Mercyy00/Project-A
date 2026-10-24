"""JARVIS Document Templates Engine (Day 6 Deliverable).

Author: Document Engineer
Role: Ready-to-use professional document templates:
      Project Reports, Assignment Covers, Resumes, and Application Letters.
"""

from datetime import datetime
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from creator.docx_maker import make_docx
from creator.pdf_maker import make_pdf
from creator.themes import contains_devanagari

logger = logging.getLogger(__name__)


def project_report(
    title: str,
    author: str,
    chapters: List[Dict[str, Any]],
    theme: str = "clean_light",
    out_dir: str = "workspace",
    kind: str = "pdf",
    auto_open: bool = False,
    header_text: Optional[str] = None,
    footer_text: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Build a comprehensive academic or corporate project report.

    Implements Day 6 template deliverable:
    - Automatically builds executive cover page with author metadata
    - Formats chapters with headings, narrative text, bullet points, and data tables/charts
    - Automatically structures Executive Summary and Conclusion sections if missing
    - Renders as high-fidelity PDF (Platypus) or Word DOCX

    Args:
        title: Project title.
        author: Author or project owner name.
        chapters: List of chapter dictionaries. Each can include:
            - 'heading' (str): Chapter title.
            - 'text' (str): Body narrative.
            - 'bullets' (list[str]): Bullet points.
            - 'metrics' (list[dict], optional): Bento grid metrics.
            - 'table' (list[list[str]], optional): Tabular data.
            - 'chart' (dict, optional): Chart definition ({'kind', 'labels', 'values', 'title'}).
        theme: Styling theme ('clean_light', 'dark_pro', 'colourful').
        out_dir: Directory where the document will be saved.
        kind: Document format ('pdf' or 'docx').
        auto_open: Whether to automatically launch the file upon creation.
        header_text: Optional running header text.
        footer_text: Optional running footer text.

    Returns:
        str: Absolute filesystem path to the created document.
    """
    try:
        sections: List[Dict[str, Any]] = []

        # 1. Executive Summary Chapter
        sections.append({
            "heading": "1. Executive Summary",
            "text": (
                f"This document represents the official technical project report for '{title}', "
                f"authored by {author}. It outlines the core architecture, implementation milestones, "
                "experimental evaluations, and operational deliverables."
            ),
            "bullets": [
                f"Primary Project Focus: {title}",
                f"Lead Engineer / Author: {author}",
                "Status: Verified & Operational",
                "Compliance: Full interface and modular isolation conformance",
            ],
        })

        # 2. User Provided Chapters
        for ch_idx, ch in enumerate(chapters, start=2):
            heading = ch.get("heading") or f"{ch_idx}. Project Milestone"
            sections.append({
                "heading": heading,
                "text": ch.get("text", ""),
                "bullets": ch.get("bullets", []),
                "metrics": ch.get("metrics"),
                "table": ch.get("table"),
                "chart": ch.get("chart"),
                "page_break_after": ch.get("page_break_after", False),
            })

        # 3. Conclusion & Next Steps
        sections.append({
            "heading": f"{len(sections) + 1}. Conclusion & Future Roadmap",
            "text": (
                "The engineering objectives described in this report have been successfully met. "
                "Subsystem performance benchmarks confirm robust stability and production readiness."
            ),
            "bullets": [
                "All test cases passed with zero regressions.",
                "Automated document rendering verified across formats.",
                "System deployed to local autonomous workspace.",
            ],
        })

        subtitle = f"Technical Project Report  •  Author: {author}"
        f_text = footer_text or f"Project Report: {title[:30]}  •  {author}"
        h_text = header_text or f"JARVIS Engineering Report  |  {title[:30]}"

        if (kind or "pdf").strip().lower() == "docx":
            return make_docx(
                title=title,
                sections=sections,
                theme=theme,
                out_dir=out_dir,
                subtitle=subtitle,
                auto_open=auto_open,
                cover_page=True,
                header_text=h_text,
                footer_text=f_text,
            )
        else:
            return make_pdf(
                title=title,
                sections=sections,
                theme=theme,
                out_dir=out_dir,
                subtitle=subtitle,
                auto_open=auto_open,
                cover_page=True,
                header_text=h_text,
                footer_text=f_text,
            )

    except Exception as exc:
        logger.error("project_report template failed: %s", exc, exc_info=True)
        raise RuntimeError(f"Failed to generate project report: {exc}") from exc


def assignment_cover(
    subject: str,
    name: str,
    roll_no: str,
    title: str = "Assignment Submission",
    theme: str = "clean_light",
    out_dir: str = "workspace",
    kind: str = "pdf",
    auto_open: bool = False,
    submission_date: Optional[str] = None,
    course_code: Optional[str] = None,
    assignment_no: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Build a formal academic assignment submission document with cover page.

    Implements Day 6 template deliverable:
    - Structured student identification metadata table
    - Formal declaration of originality and integrity
    - Assignment rubric and evaluation framework
    - Renders as high-fidelity PDF or Word DOCX

    Args:
        subject: Course or subject name (e.g. 'Artificial Intelligence', 'Operating Systems').
        name: Student full name.
        roll_no: Student roll number or registration ID.
        title: Title of the assignment (default: 'Assignment Submission').
        theme: Theme name ('clean_light', 'dark_pro', 'colourful').
        out_dir: Output directory.
        kind: Document format ('pdf' or 'docx').
        auto_open: Whether to automatically open the document.
        submission_date: Date string (defaults to current date).
        course_code: Optional academic course identifier.
        assignment_no: Optional assignment number.

    Returns:
        str: Absolute filesystem path to the created assignment document.
    """
    try:
        sub_date = submission_date or datetime.now().strftime("%B %d, %Y")
        doc_title = f"{subject} — {title}"

        details_table = [
            ["STUDENT NAME", name],
            ["ROLL NUMBER", roll_no],
            ["SUBJECT / COURSE", subject],
            ["COURSE CODE", course_code or "CS-2026"],
            ["ASSIGNMENT NO", assignment_no or "Assignment 1"],
            ["SUBMISSION DATE", sub_date],
            ["STATUS", "Submitted for Assessment"],
        ]

        sections: List[Dict[str, Any]] = [
            {
                "heading": "Candidate & Submission Particulars",
                "text": "The particulars below confirm the official registration of this assignment submission.",
                "table": details_table,
            },
            {
                "heading": "Academic Integrity & Declaration",
                "text": (
                    f"I, {name} (Roll No: {roll_no}), hereby declare that this assignment "
                    f"submitted for the course '{subject}' represents my own individual work, "
                    "researched and prepared in compliance with academic standards of integrity."
                ),
                "bullets": [
                    "All code and technical implementations have been locally verified.",
                    "No unauthorized collaboration or plagiarism took place.",
                    "All referenced documentation and third-party libraries have been acknowledged.",
                ],
            },
            {
                "heading": "Assessment & Evaluation Criteria",
                "text": "Evaluation parameters for institutional scoring and feedback:",
                "table": [
                    ["Evaluation Parameter", "Weight", "Grade / Score"],
                    ["Correctness & Functionality", "40%", "Pending"],
                    ["Code Quality & Documentation", "30%", "Pending"],
                    ["Design, Theming & Polish", "20%", "Pending"],
                    ["Viva & Verbal Articulation", "10%", "Pending"],
                ],
            },
        ]

        subtitle = f"{subject}  •  Submitted by {name} ({roll_no})"
        f_text = f"{subject}  •  {name} ({roll_no})  •  JARVIS Academic Suite"
        h_text = f"Assignment Submission: {subject}"

        if (kind or "pdf").strip().lower() == "docx":
            return make_docx(
                title=doc_title,
                sections=sections,
                theme=theme,
                out_dir=out_dir,
                subtitle=subtitle,
                auto_open=auto_open,
                cover_page=True,
                header_text=h_text,
                footer_text=f_text,
            )
        else:
            return make_pdf(
                title=doc_title,
                sections=sections,
                theme=theme,
                out_dir=out_dir,
                subtitle=subtitle,
                auto_open=auto_open,
                cover_page=True,
                header_text=h_text,
                footer_text=f_text,
            )

    except Exception as exc:
        logger.error("assignment_cover template failed: %s", exc, exc_info=True)
        raise RuntimeError(f"Failed to generate assignment cover: {exc}") from exc


def resume(
    data: Dict[str, Any],
    theme: str = "clean_light",
    out_dir: str = "workspace",
    kind: str = "pdf",
    auto_open: bool = False,
    **kwargs: Any,
) -> str:
    """Build a professional, modern curriculum vitae / resume.

    Implements Day 6 template deliverable:
    - Formats contact details, career summary, technical skills,
      work experience, and education
    - Single/multi-page compact layout without separate cover page
    - Renders as high-fidelity PDF or Word DOCX

    Args:
        data: Resume content dictionary. Supports:
            - 'name' (str): Full candidate name.
            - 'title' / 'role' (str): Professional headline.
            - 'contact' (dict or str): Email, phone, location, linkedin, github.
            - 'summary' (str): Professional summary paragraph.
            - 'skills' (list[str] or dict): Technical skills breakdown.
            - 'experience' (list[dict]): Work history items.
            - 'education' (list[dict]): Academic history items.
            - 'projects' (list[dict]): Portfolio projects.
        theme: Theme name ('clean_light', 'dark_pro', 'colourful').
        out_dir: Target output directory.
        kind: Document format ('pdf' or 'docx').
        auto_open: Whether to automatically open the document.

    Returns:
        str: Absolute filesystem path to the created resume.
    """
    try:
        candidate_name = data.get("name", "Software Engineer")
        target_role = data.get("role") or data.get("title", "Technical Professional")

        sections: List[Dict[str, Any]] = []

        # 1. Contact Particulars & Headline
        contact = data.get("contact", {})
        if isinstance(contact, dict):
            c_lines = [f"{k.title()}: {v}" for k, v in contact.items()]
            c_text = "  •  ".join(c_lines)
        else:
            c_text = str(contact)

        # 2. Executive Professional Summary
        summary = data.get(
            "summary",
            (
                f"Results-driven {target_role} with proven expertise in building autonomous AI systems, "
                "resilient distributed architectures, and programmatic document engines. "
                "Committed to rigorous engineering standards, clean code, and modular isolation."
            ),
        )
        sections.append({
            "heading": "Professional Profile",
            "text": summary,
            "bullets": [f"Contact: {c_text}"] if c_text else [],
        })

        # 3. Technical Skills
        skills = data.get("skills")
        if skills:
            if isinstance(skills, dict):
                skill_table = [["Category", "Competencies"]]
                for cat, item in skills.items():
                    items_str = ", ".join(item) if isinstance(item, list) else str(item)
                    skill_table.append([cat, items_str])
                sections.append({
                    "heading": "Technical Skills & Competencies",
                    "table": skill_table,
                })
            elif isinstance(skills, list):
                sections.append({
                    "heading": "Technical Skills",
                    "bullets": [str(s) for s in skills],
                })

        # 4. Professional Experience
        exp_list = data.get("experience", [])
        if exp_list and isinstance(exp_list, list):
            exp_bullets: List[str] = []
            for item in exp_list:
                role_str = item.get("role", "Engineer")
                comp_str = item.get("company", "Technology Corp")
                period_str = item.get("period", "2024 - Present")
                header_line = f"<b>{role_str}</b> at {comp_str} ({period_str})"
                exp_bullets.append(header_line)
                for b in item.get("bullets", []):
                    exp_bullets.append(f"  - {b}")

            sections.append({
                "heading": "Work Experience",
                "bullets": exp_bullets,
            })

        # 5. Key Projects
        proj_list = data.get("projects", [])
        if proj_list and isinstance(proj_list, list):
            proj_bullets: List[str] = []
            for p in proj_list:
                p_name = p.get("name", "Project")
                p_desc = p.get("description", "")
                p_tech = p.get("tech", "")
                p_line = f"<b>{p_name}</b>: {p_desc}" + (f" <i>[{p_tech}]</i>" if p_tech else "")
                proj_bullets.append(p_line)

            sections.append({
                "heading": "Key Projects & Deliverables",
                "bullets": proj_bullets,
            })

        # 6. Education
        edu_list = data.get("education", [])
        if edu_list and isinstance(edu_list, list):
            edu_table = [["Degree / Qualification", "Institution", "Year", "Score / Honors"]]
            for edu in edu_list:
                edu_table.append([
                    str(edu.get("degree", "Bachelor of Engineering")),
                    str(edu.get("institution", "University")),
                    str(edu.get("year", "2026")),
                    str(edu.get("grade", edu.get("score", "First Class"))),
                ])
            sections.append({
                "heading": "Education & Academic Credentials",
                "table": edu_table,
            })

        doc_title = candidate_name
        subtitle = target_role
        f_text = f"Resume  •  {candidate_name}  •  {target_role}"
        h_text = f"{candidate_name} | Curriculum Vitae"

        # Resumes use compact cover_page=False so content begins immediately on page 1
        if (kind or "pdf").strip().lower() == "docx":
            return make_docx(
                title=doc_title,
                sections=sections,
                theme=theme,
                out_dir=out_dir,
                subtitle=subtitle,
                auto_open=auto_open,
                cover_page=False,
                header_text=h_text,
                footer_text=f_text,
            )
        else:
            return make_pdf(
                title=doc_title,
                sections=sections,
                theme=theme,
                out_dir=out_dir,
                subtitle=subtitle,
                auto_open=auto_open,
                cover_page=False,
                header_text=h_text,
                footer_text=f_text,
            )

    except Exception as exc:
        logger.error("resume template failed: %s", exc, exc_info=True)
        raise RuntimeError(f"Failed to generate resume: {exc}") from exc


def application_letter(
    data: Dict[str, Any],
    theme: str = "clean_light",
    out_dir: str = "workspace",
    kind: str = "pdf",
    auto_open: bool = False,
    **kwargs: Any,
) -> str:
    """Build a formal business or job application cover letter.

    Implements Day 6 template deliverable:
    - Formal letter formatting with Date, Recipient block, Subject line
    - Salutation, structured narrative body paragraphs, and professional sign-off
    - Directly begins on page 1 without extraneous cover page
    - Renders as high-fidelity PDF or Word DOCX

    Args:
        data: Letter content dictionary. Supports:
            - 'applicant_name' (str): Full name of the applicant.
            - 'applicant_contact' (str or dict): Email, phone, or address.
            - 'recipient_name' (str): Name of recipient (e.g. 'Hiring Manager').
            - 'recipient_title' (str): Recipient designation / title.
            - 'company_name' (str): Organization or institutional name.
            - 'date' (str, optional): Date of letter.
            - 'subject' (str): Letter subject line.
            - 'salutation' (str, optional): e.g. 'Dear Hiring Team,'.
            - 'body_paragraphs' (list[str]): Narrative body paragraphs.
            - 'sign_off' (str, optional): e.g. 'Sincerely,'.
        theme: Theme name ('clean_light', 'dark_pro', 'colourful').
        out_dir: Target output directory.
        kind: Document format ('pdf' or 'docx').
        auto_open: Whether to automatically open the document.

    Returns:
        str: Absolute filesystem path to the created application letter.
    """
    try:
        app_name = data.get("applicant_name", "Applicant")
        app_contact = data.get("applicant_contact", "applicant@example.com")
        rec_name = data.get("recipient_name", "Hiring Manager")
        rec_title = data.get("recipient_title", "Head of Talent Acquisition")
        comp_name = data.get("company_name", "Prospective Enterprise")
        letter_date = data.get("date") or datetime.now().strftime("%B %d, %Y")
        subject = data.get("subject", "Application for Professional Position")
        salutation = data.get("salutation", f"Dear {rec_name},")
        sign_off = data.get("sign_off", "Sincerely,")

        body_paragraphs = data.get("body_paragraphs", [])
        if not body_paragraphs:
            body_paragraphs = [
                (
                    f"I am writing to formally submit my application for the consideration of opportunities "
                    f"at {comp_name}. With a proven track record in software engineering, autonomous systems, "
                    "and full-lifecycle document generation, I am eager to contribute to your team's mission."
                ),
                (
                    "Throughout my career, I have prioritized modular code quality, test-driven development, "
                    "and performance optimization. I have demonstrated agility in implementing complex multi-modal "
                    "workflows while maintaining 100% compliance with team architectural specifications."
                ),
                (
                    f"Thank you for your time and thoughtful consideration. I welcome the opportunity to discuss "
                    f"how my technical background and creative problem solving can add immediate value to {comp_name}."
                ),
            ]

        sections: List[Dict[str, Any]] = []

        # 1. Formal Recipient & Date Particulars
        letter_meta = [
            ["DATE", letter_date],
            ["TO", f"{rec_name}\n{rec_title}\n{comp_name}"],
            ["FROM", f"{app_name}\n{app_contact}"],
            ["RE", subject],
        ]
        sections.append({
            "heading": f"Subject: {subject}",
            "text": f"{salutation}\n\n{body_paragraphs[0]}",
            "table": letter_meta,
        })

        # 2. Subsequent Narrative Paragraphs
        for p_idx, para in enumerate(body_paragraphs[1:], start=2):
            sections.append({
                "heading": "",
                "text": para,
            })

        # 3. Sign-off and Signature Block
        sections.append({
            "heading": "",
            "text": f"{sign_off}\n\n\n<b>{app_name}</b>\n{app_contact}",
        })

        doc_title = f"Application Letter — {app_name}"
        subtitle = f"{subject}  •  {comp_name}"
        f_text = f"Formal Application  •  {app_name}  •  {comp_name}"
        h_text = f"Application: {subject[:35]}"

        # Application letters start on page 1 without a separate cover page
        if (kind or "pdf").strip().lower() == "docx":
            return make_docx(
                title=doc_title,
                sections=sections,
                theme=theme,
                out_dir=out_dir,
                subtitle=subtitle,
                auto_open=auto_open,
                cover_page=False,
                header_text=h_text,
                footer_text=f_text,
            )
        else:
            return make_pdf(
                title=doc_title,
                sections=sections,
                theme=theme,
                out_dir=out_dir,
                subtitle=subtitle,
                auto_open=auto_open,
                cover_page=False,
                header_text=h_text,
                footer_text=f_text,
            )

    except Exception as exc:
        logger.error("application_letter template failed: %s", exc, exc_info=True)
        raise RuntimeError(f"Failed to generate application letter: {exc}") from exc
