#!/usr/bin/env python3
"""Drop-in wrapper: whisper.cpp for yt_pipeline.sh (OpenAI-whisper CLI compatible)."""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

WHISPER_CPP = Path.home() / ".local/src/whisper.cpp/build/bin/whisper-cli"
MODEL_DIR = Path.home() / ".cache/whisper.cpp"


def model_path(name: str, language: str = "") -> Path:
    name = name.lower()
    # Prefer .en model for English content on non-large models
    if language.lower().startswith("en") and name not in ("large", "large-v1", "large-v2", "large-v3", "turbo"):
        for suffix in [f"{name}.en", name]:
            p = MODEL_DIR / f"ggml-{suffix}.bin"
            if p.exists():
                return p
    else:
        for suffix in [name, f"{name}.en"]:
            p = MODEL_DIR / f"ggml-{suffix}.bin"
            if p.exists():
                return p
    raise FileNotFoundError(f"No whisper.cpp model found for {name} in {MODEL_DIR}")


def ensure_model(name: str, language: str = "") -> Path:
    try:
        return model_path(name, language)
    except FileNotFoundError:
        script = Path.home() / ".local/src/whisper.cpp/models/download-ggml-model.sh"
        download_name = name
        if language.lower().startswith("en") and name not in ("large", "large-v1", "large-v2", "large-v3", "turbo"):
            download_name = f"{name}.en"
        subprocess.run(["bash", str(script), download_name, str(MODEL_DIR)], check=True)
        return model_path(name, language)


def detect_language(stderr: str) -> str:
    for pat in [r"auto-detected language:\s*([a-zA-Z-]+)", r"Detected language:\s*([a-zA-Z-]+)"]:
        m = re.search(pat, stderr)
        if m:
            return m.group(1)
    return "zh"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("--model", default="base")
    parser.add_argument("--language", default="")
    parser.add_argument("--task", default="transcribe", choices=["transcribe", "translate"])
    parser.add_argument("--output_format", default="txt", choices=["txt", "srt"])
    parser.add_argument("--output_dir", default=".")
    args = parser.parse_args()

    if not WHISPER_CPP.exists():
        print(f"whisper-cli not found at {WHISPER_CPP}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lang = args.language or "auto"

    # For auto detection, do a quick txt run on a 30s sample and extract language
    if lang.lower() == "auto":
        prefix = output_dir / args.audio.stem
        # Use a 30-second sample so long audio doesn't slow detection
        sample_wav = Path(tempfile.gettempdir()) / f"whisper_auto_sample_{args.audio.stem}.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(args.audio), "-t", "30", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(sample_wav)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
        )
        cmd = [
            str(WHISPER_CPP), "-m", str(ensure_model(args.model, "")),
            "-f", str(sample_wav), "-l", "auto",
            "-otxt", "-of", str(prefix)
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        try:
            sample_wav.unlink()
        except FileNotFoundError:
            pass
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            sys.exit(result.returncode)
        detected = detect_language(result.stderr)
        msg = f"Detected language: {detected}"
        print(msg)
        print(msg, file=sys.stderr)
        txt = Path(f"{prefix}.txt")
        if txt.exists():
            print(txt.read_text(encoding="utf-8"))
        return

    # Normal run with explicit language
    prefix = output_dir / args.audio.stem
    cmd = [
        str(WHISPER_CPP), "-m", str(ensure_model(args.model, lang)),
        "-f", str(args.audio), "-l", lang, "-of", str(prefix)
    ]
    if args.task.lower() == "translate":
        cmd.append("--translate")

    if args.output_format == "srt":
        cmd.append("-osrt")
    elif args.output_format == "txt":
        cmd.append("-otxt")

    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    if args.output_format == "txt":
        txt_file = Path(f"{prefix}.txt")
        if txt_file.exists():
            print(txt_file.read_text(encoding="utf-8"))
    # For srt, just ensure file exists; pipeline will consume it
    out_file = Path(f"{prefix}.{args.output_format}")
    if not out_file.exists():
        # whisper-cli might write prefix.wav.srt in some versions; search fallback
        candidates = list(output_dir.glob(f"{prefix.name}*.srt"))
        if candidates:
            candidates[0].rename(out_file)


if __name__ == "__main__":
    main()
