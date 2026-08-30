#!/usr/bin/env python3
"""Generic 繁體中文 summary PDF renderer — DEFAULT FONT: Noto Sans CJK TC.

Renders via WeasyPrint (HTML/CSS → PDF) so it fully supports Noto Sans CJK
(presented as OpenType/CFF .ttc; reportlab cannot load CFF outlines).
Font resolution goes through fontconfig — Regular + Bold picked automatically.

Usage (same CLI as the old reportlab version):
    python render_summary_pdf.py \\
        --output out.pdf \\
        --title "主標題" \\
        --subtitle "副標題" \\
        --video-id "VIDEO" \\
        --channel "Channel" \\
        --duration "20:22" \\
        --upload-date "2026-08-01" \\
        --language "zh-Hans" \\
        --views "123,456" \\
        --source "YouTube auto-sub via yt-dlp" \\
        --tldr "一句話總結。" \\
        --body "section1\\nbody1\\n\\nsection2\\nbody2" \\
        --quotes "quote1\\nquote2"

Body format: alternating H2 section title + paragraph text, separated by blank line.
Lines starting with '• ' are rendered as bullet paragraphs.

Fonts (fontconfig names):
  - body / headings : "Noto Sans CJK TC"  (falls back to SC, then sans-serif)
  - Default for ALL agents; edit $DEFAULT_FONT here to change globally.
"""
import argparse
import html
import os

# ── Default fonts (apply to all agents) ──────────────────────────────
# English/Latin → DejaVu Sans Mono; Chinese → Noto Sans CJK TC
# fontconfig picks the right face per glyph automatically.
DEFAULT_FONT = "'DejaVu Sans Mono', 'Noto Sans CJK TC', 'Noto Sans CJK SC', monospace"
FONT_PATH_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_PATH_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
# ──────────────────────────────────────────────────────────────────────

CSS_TEMPLATE = """
@page {{ size: A4; margin: 14mm; }}
body {{
  font-family: {font};
  color: #222;
  font-size: 10.5pt;
  line-height: 1.65;
}}
h1 {{
  text-align: center; color: #0a3d62; font-size: 20pt;
  margin: 0 0 2px 0;
}}
.sub {{
  text-align: center; color: #7f8c8d; font-size: 10pt;
  margin-bottom: 16px;
}}
h2 {{
  color: #1e6091; font-size: 12.5pt; font-weight: bold;
  margin: 14px 0 5px 0;
  border-bottom: 1px solid #dbe4ec; padding-bottom: 2px;
}}
p {{ margin: 4px 0; }}
.bullet {{ margin-left: 16px; }}
.quote {{
  color: #3d566e; margin: 5px 20px; padding: 6px 12px;
  border-left: 3px solid #85c1e9; background: #f4f8fc;
}}
.meta {{ text-align: center; color: #95a5a6; font-size: 8.5pt; }}
.foot {{ text-align: center; color: #aaa; font-size: 8pt; margin-top: 14px; }}
table {{ border-collapse: collapse; width: 100%; margin: 6px 0; font-size: 9.5pt; }}
th {{ background: #1e6091; color: #fff; text-align: left; padding: 5px 8px; }}
td {{ border: 1px solid #d5dbdb; padding: 5px 8px; }}
tr:nth-child(even) td {{ background: #f4f8fc; }}
"""


def esc(t):
    return html.escape(t or "", quote=False)


def build(args):
    parts = []
    parts.append(f"<!DOCTYPE html><html lang='zh-Hant'><head><meta charset='UTF-8'>")
    parts.append(f"<style>{CSS_TEMPLATE.format(font=DEFAULT_FONT)}</style></head><body>")

    # Title / subtitle
    parts.append(f"<h1>{esc(args.title)}</h1>")
    if args.subtitle:
        parts.append(f"<div class='sub'>{esc(args.subtitle)}</div>")
    parts.append(f"<div class='meta'>{esc(args.video_id or '')}</div>")

    # Info table
    info_rows = []
    for label, val in [("頻道", args.channel), ("影片 ID", args.video_id),
                       ("時長", args.duration), ("上傳日期", args.upload_date),
                       ("語言", args.language), ("觀看次數", args.views),
                       ("取得方式", args.source)]:
        if val:
            info_rows.append(f"<tr><td><b>{esc(label)}</b></td><td>{esc(val)}</td></tr>")
    if info_rows:
        parts.append("<table>" + "".join(info_rows) + "</table>")

    # TL;DR
    if args.tldr:
        parts.append(f"<h2>一句話總結</h2>")
        parts.append(f"<div class='quote'>{esc(args.tldr)}</div>")

    # Body: alternate H2 section + paragraph, separated by blank line
    if args.body:
        for blk in args.body.split("\n\n"):
            blk = blk.strip()
            if not blk:
                continue
            lines = blk.split("\n", 1)
            if len(lines) == 2:
                parts.append(f"<h2>{esc(lines[0])}</h2>")
                for para in lines[1].split("\n"):
                    para = para.strip()
                    if not para:
                        continue
                    cls = "bullet" if para.startswith("• ") else ""
                    parts.append(f"<p class='{cls}'>{esc(para)}</p>")
            else:
                parts.append(f"<p>{esc(blk)}</p>")

    # Quotes
    if args.quotes:
        parts.append("<h2>值得留下來的金句</h2>")
        for q in args.quotes.split("\n"):
            q = q.strip()
            if q:
                parts.append(f"<div class='quote'>{esc(q)}</div>")

    parts.append("<div class='foot'>— PDF rendered by DS Agent · Noto Sans CJK TC —</div>")
    parts.append("</body></html>")
    html_str = "".join(parts)

    # Validate font file exists (early, clear error)
    if not os.path.exists(FONT_PATH_REG):
        raise SystemExit(
            f"❌ Noto Sans CJK 字體唔存在: {FONT_PATH_REG}\n"
            "安裝: sudo apt install -y fonts-noto-cjk"
        )

    from weasyprint import HTML
    HTML(string=html_str).write_pdf(args.output)
    print(f"PDF built → {args.output}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle", default="")
    p.add_argument("--channel", default="")
    p.add_argument("--video-id", default="")
    p.add_argument("--duration", default="")
    p.add_argument("--upload-date", default="")
    p.add_argument("--language", default="")
    p.add_argument("--views", default="")
    p.add_argument("--source", default="")
    p.add_argument("--tldr", default="")
    p.add_argument("--body", default="")
    p.add_argument("--quotes", default="")
    args = p.parse_args()
    build(args)
