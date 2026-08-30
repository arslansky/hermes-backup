#!/usr/bin/env python3
"""
Convert SRT/VTT subtitle to two text formats:
- timed.txt: [HH:MM:SS] text
- clean.txt: text only

Usage:
    srt_to_transcripts.py <input.{srt|vtt}> <output_dir> [--dedupe]

Options:
    --dedupe    Enable dedupe for YT English auto-captions (rolling window)
                Dedupe logic: detect consecutive repeated lines (same text
                within last 3 entries), keep only first occurrence.
                YT English auto-caption VTT uses rolling window pattern,
                each line of speech appears ~3 times.
"""
import re
import sys
from pathlib import Path


def srt_time_to_hms(ts: str) -> str:
    """00:00:05,040 (SRT) or 00:00:05.040 (VTT) -> [00:00:05]"""
    h, m, s = ts.split(":")
    s = s.replace(",", ".").split(".")[0]
    return f"[{h}:{m}:{s}]"


def parse_srt(srt_text: str):
    """Parse SRT or VTT — returns list of (start_str_hms, text) tuples."""
    # VTT: strip WEBVTT header block before first timestamp
    srt_text = re.sub(r"^WEBVTT.*?\n\n", "", srt_text.strip(), flags=re.DOTALL)
    blocks = re.split(r"\n\s*\n", srt_text.strip())
    out = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        # VTT sometimes has inline cue settings on time line
        # SRT may have index line
        time_idx = None
        for idx, ln in enumerate(lines):
            if "-->" in ln:
                time_idx = idx
                break
        if time_idx is None:
            continue
        time_line = lines[time_idx]
        time_match = re.match(r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->", time_line)
        if not time_match:
            continue
        start = srt_time_to_hms(time_match.group(1))
        text_lines = lines[time_idx + 1:]
        # strip VTT inline tags like <c.color>, <00:00:01.000>
        cleaned = []
        for t in text_lines:
            t = re.sub(r"<[^>]+>", "", t).strip()
            if t:
                cleaned.append(t)
        text = " ".join(cleaned)
        if text:
            out.append((start, text))
    return out


def dedupe_consecutive(segments):
    """
    Dedupe consecutive repeating lines (YT English auto-caption rolling window).
    
    YT English auto-caption VTT uses a rolling window pattern where each
    line of speech appears ~3 times with slightly different timestamps.
    This dedupes by keeping only the first occurrence when the same text
    appears within the last WINDOW entries.
    
    v2: window 擴大到 5 + 含 fuzzy（去除空白後）比對，捉到更多殘留重複。
    """
    WINDOW = 5
    seen_texts = []  # sliding window of last N unique texts
    result = []
    for ts, text in segments:
        text_clean = "".join(text.strip().lower().split())  # 去空白做 fuzzy 比對
        if not text_clean:
            continue
        # Check if text matches any of the last N entries
        is_dup = False
        for prev_text in seen_texts[-WINDOW:]:
            # 完全相等 或 一方係另一方 substring
            if text_clean == prev_text or text_clean in prev_text or prev_text in text_clean:
                is_dup = True
                break
        if is_dup:
            continue
        seen_texts.append(text_clean)
        result.append((ts, text))
    return result


def main():
    if len(sys.argv) < 3:
        print("Usage: srt_to_transcripts.py <input.{srt|vtt}> <output_dir> [--dedupe]", file=sys.stderr)
        sys.exit(2)

    srt_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    enable_dedupe = "--dedupe" in sys.argv

    srt = srt_path.read_text(encoding="utf-8")
    parsed = parse_srt(srt)

    orig_count = len(parsed)

    if enable_dedupe:
        parsed = dedupe_consecutive(parsed)
        dedup_count = len(parsed)
        dedup_pct = round((1 - dedup_count / orig_count) * 100, 1) if orig_count > 0 else 0
        print(f"🧹 Dedupe: {orig_count} → {dedup_count} segments ({dedup_pct}% reduction)")

    stem = srt_path.stem
    # Detect lang from filename: if stem ends with .zh-TW or .en, use that
    m = re.search(r"\.(zh-[A-Za-z]+|en|[a-z]{2})$", stem)
    if m:
        lang = m.group(1)
        base = stem[:-(len(lang) + 1)]
    else:
        lang = "zh-Hans"
        base = stem

    timed_path = out_dir / f"{base}.timed.{lang}.txt"
    clean_path = out_dir / f"{base}.{lang}.txt"

    with timed_path.open("w", encoding="utf-8") as f:
        for ts, text in parsed:
            f.write(f"{ts} {text}\n")
    with clean_path.open("w", encoding="utf-8") as f:
        for _, text in parsed:
            f.write(f"{text}\n")

    print(f"wrote {timed_path} ({timed_path.stat().st_size} bytes, {len(parsed)} segments)")
    print(f"wrote {clean_path} ({clean_path.stat().st_size} bytes, {len(parsed)} segments)")


if __name__ == "__main__":
    main()