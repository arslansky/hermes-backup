#!/usr/bin/env python3
"""
Drop-in wrapper: whisper.cpp for the yt_pipeline.sh Whisper calls.

Supported invocation (mirrors openai-whisper CLI):
  whisper <audio.wav> --model {tiny,base,small,medium,large} --language <lang|auto>
        --task {transcribe,translate} --output_format {txt,srt} --output_dir <dir>

Maps to ~/.cache/whisper.cpp/ggml-<model>.bin and calls whisper-cli.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

WHISPER_CPP = Path.home() / ".local/src/whisper.cpp/build/bin/whisper-cli"
MODEL_DIR = Path.home() / ".cache/whisper.cpp"


def model_path(name: str, language: str = "") -> Path:
    """Pick .en model if language is explicitly en, otherwise multilingual."""
    name = name.lower()
    if language.lower().startswith("en") and name not in ("large", "large-v3", "large-v2", "large-v1", "turbo"):
        candidate = MODEL_DIR / f"ggml-{name}.en.bin"
        if candidate.exists():
            return candidate
        # fallback to multilingual
        candidate = MODEL_DIR / f"ggml-{name}.bin"
        if candidate.exists():
            return candidate
    else:
        candidate = MODEL_DIR / f"ggml-{name}.bin"
        if candidate.exists():
            return candidate
        # fallback to .en
        candidate = MODEL_DIR / f"ggml-{name}.en.bin"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No whisper.cpp model found for {name} in {MODEL_DIR}")


def ensure_model(name: str, language: str = "") -> Path:
    """Try to use existing model; if missing, download via upstream script."""
    try:
        return model_path(name, language)
    except FileNotFoundError:
        script = Path.home() / ".local/src/whisper.cpp/models/download-ggml-model.sh"
        download_name = name
        if language.lower().startswith("en") and name not in ("large", "large-v3", "large-v2", "large-v1", "turbo"):
            download_name = f"{name}.en"
        subprocess.run(["bash", str(script), download_name, str(MODEL_DIR)], check=True)
        return model_path(name, language)


def run_whisper_cli(audio: Path, model: Path, language: str, task: str, output_dir: Path, out_fmt: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / audio.stem
    # whisper-cli writes <prefix>.srt or <prefix>.txt
    out_file = Path(f"{prefix}.{out_fmt}")

    cmd = [str(WHISPER_CPP), "-m", str(model), "-f", str(audio), "-of", str(prefix)]
    if out_fmt == "srt":
        cmd.append("-osrt")
    elif out_fmt == "txt":
        cmd.append("-otxt")

    if language and language.lower() != "auto":
        cmd.extend(["-l", language])
    # whisper.cpp defaults to transcribe; for translate add --translate
    if task.lower() == "translate":
        cmd.append("--translate")

    # whisper-cli prints a lot; keep stderr for detection, suppress stdout
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)

    # whisper-cli writes prefix.<ext>; ensure it exists and print like whisper
    if out_file.exists():
        if out_fmt == "txt":
            print(out_file.read_text(encoding="utf-8"))
    return out_file


def detect_language(stderr: str) -> str:
    """Parse whisper-cli stderr for detected language."""
    # whisper.cpp may print lines like:
    # auto-detected language: en (p = 0.99)
    m = re.search(r"auto-detected language:\s*([a-zA-Z-]+)", stderr)
    if m:
        return m.group(1)
    # Older format
    m = re.search(r"Detected language:\s*([a-zA-Z-]+)", stderr)
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

    model = ensure_model(args.model, args.language)
    output_dir = Path(args.output_dir)
    lang = args.language or "auto"

    # For language auto detection we need stderr
    if lang.lower() == "auto":
        output_dir.mkdir(parents=True, exist_ok=True)
        prefix = output_dir / args.audio.stem
        cmd = [str(WHISPER_CPP), "-m", str(model), "-f", str(args.audio), "-l", "auto", "-otxt", "-of", str(prefix)]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            sys.exit(result.returncode)
        lang = detect_language(result.stderr)
        msg = f"Detected language: {lang}"
        print(msg)
        print(msg, file=sys.stderr)
        txt_file = Path(f"{prefix}.txt")
        if txt_file.exists():
            print(txt_file.read_text(encoding="utf-8"))
        return

    run_whisper_cli(args.audio, model, lang, args.task, output_dir, args.output_format)


if __name__ == "__main__":
    main()
