#!/usr/bin/env python3
"""Render the Japanese report draft (Markdown) into a formatted PDF.

Minimal Markdown subset is supported: #/## headings, > blockquote,
- bullet lists, 1./2. numbered lists, **bold**, `code`, and --- rules.
This is tailored to this project's report draft, not a general converter.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem,
)

FONT_DIR = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Meiryo", str(FONT_DIR / "meiryo.ttc"), subfontIndex=0))
pdfmetrics.registerFont(TTFont("MeiryoB", str(FONT_DIR / "meiryob.ttc"), subfontIndex=0))

STYLES = {
    "title": ParagraphStyle("title", fontName="MeiryoB", fontSize=17, leading=22,
                             spaceAfter=10),
    "quote": ParagraphStyle("quote", fontName="Meiryo", fontSize=9, leading=13,
                             textColor="#555555", leftIndent=8, spaceAfter=3),
    "h2": ParagraphStyle("h2", fontName="MeiryoB", fontSize=13, leading=18,
                          spaceBefore=14, spaceAfter=6,
                          borderColor="#2b6cb0", borderWidth=0,
                          textColor="#1a365d"),
    "body": ParagraphStyle("body", fontName="Meiryo", fontSize=10, leading=15,
                            spaceAfter=4, alignment=4),  # 4 = justify
    "li": ParagraphStyle("li", fontName="Meiryo", fontSize=10, leading=15,
                          spaceAfter=3),
    "li_num": ParagraphStyle("li_num", fontName="Meiryo", fontSize=10, leading=15,
                              spaceAfter=5, leftIndent=14, firstLineIndent=-14),
}


def inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font color="#8a2be2">\1</font>', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<link href="\2" color="#2b6cb0">\1</link>', text)
    return text


def build_story(markdown_text: str) -> list:
    story: list = []
    lines = markdown_text.splitlines()
    i = 0
    n = len(lines)

    def flush_list(items: list[str], ordered: bool):
        if not items:
            return
        if ordered:
            for idx, t in enumerate(items, start=1):
                story.append(Paragraph(f"{idx}. {inline(t)}", STYLES["li_num"]))
            story.append(Spacer(1, 4))
            return
        flow_items = [ListItem(Paragraph(inline(t), STYLES["li"]), leftIndent=14) for t in items]
        story.append(ListFlowable(
            flow_items,
            bulletType="bullet",
            leftIndent=10,
            bulletFontName="Meiryo",
            bulletFontSize=10,
        ))
        story.append(Spacer(1, 4))

    while i < n:
        raw = lines[i]
        line = raw.strip()
        if not line:
            i += 1
            continue
        if line == "---":
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", color="#cccccc", thickness=0.6))
            story.append(Spacer(1, 8))
            i += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), STYLES["title"]))
            i += 1
            continue
        if line.startswith("## ") or line.startswith("### "):
            text = line.split(" ", 1)[1]
            story.append(Paragraph(inline(text), STYLES["h2"]))
            story.append(HRFlowable(width="100%", color="#1a365d", thickness=1.1, spaceAfter=6))
            i += 1
            continue
        if line.startswith("> "):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            story.append(Paragraph(inline(" ".join(buf)), STYLES["quote"]))
            continue
        if re.match(r"^[-*] ", line):
            items = []
            while i < n and re.match(r"^[-*] ", lines[i].strip()):
                items.append(re.sub(r"^[-*] ", "", lines[i].strip()))
                i += 1
            flush_list(items, ordered=False)
            continue
        if re.match(r"^\d+\. ", line):
            items = []
            while i < n and re.match(r"^\d+\. ", lines[i].strip()):
                items.append(re.sub(r"^\d+\. ", "", lines[i].strip()))
                i += 1
            flush_list(items, ordered=True)
            continue
        if re.match(r"^- \[ \] ", line):
            items = []
            while i < n and lines[i].strip().startswith("- [ ] "):
                items.append(lines[i].strip()[6:])
                i += 1
            flush_list(items, ordered=False)
            continue
        # paragraph: collect continuation lines (simple wrap handling)
        buf = [line]
        i += 1
        while i < n and lines[i].strip() and not re.match(
            r"^(#|>|-|\*|\d+\.|---)", lines[i].strip()
        ):
            buf.append(lines[i].strip())
            i += 1
        story.append(Paragraph(inline(" ".join(buf)), STYLES["body"]))

    return story


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    doc = SimpleDocTemplate(
        str(args.output), pagesize=A4,
        topMargin=18 * mm, bottomMargin=18 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
        title="PAI\u6700\u7d42\u8ab2\u984c \u8aac\u660e\u8cc7\u6599",
    )
    doc.build(build_story(text))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
