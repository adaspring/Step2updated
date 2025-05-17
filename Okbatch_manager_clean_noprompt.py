import os
import json
import subprocess
from pathlib import Path
import argparse

UPLOAD_DIR = "uploaded_files"
PROCESSED_DIR = "processed_files"
CHARACTER_LIMIT_PRE = 100000
CHARACTER_LIMIT_POST = 40000

def estimate_html_size(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return len(content)

def count_json_text_chars(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return sum(
        len(block.get("text", "")) +
        sum(len(seg) for seg in block.get("segments", {}).values())
        for block in data.values()
    )

def run_extraction(file_path, lang):
    print(f"Running extraction for {file_path}")
    result = subprocess.run([
        "python", "Finalstep1_extract.py",
        file_path,
        "--lang", lang
    ])
    if result.returncode != 0:
        raise RuntimeError(f"Extraction failed for {file_path}")

def run_translation(json_path, lang, primary_lang, secondary_lang, memory_dir):
    print(f"Running translation for {json_path}")
    command = [
        "python", "Finalstep2_translate.py",
        "--input", json_path,
        "--output", "translations.json",
        "--lang", lang,
        "--primary-lang", primary_lang,
        "--memory", memory_dir,
        "--skip-if-cached"
    ]
    if secondary_lang:
        command += ["--secondary-lang", secondary_lang]

    result = subprocess.run(command)
    if result.returncode != 0:
        raise RuntimeError(f"Translation failed for {json_path}")

def ensure_dirs():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_args():
    parser = argparse.ArgumentParser(
        description="Run batch extraction and translation using Script 1 and Script 2"
    )
    parser.add_argument("--lang", required=True, help="Target translation language")
    parser.add_argument("--primary-lang", required=True, help="Primary source language")
    parser.add_argument("--secondary-lang", help="Optional secondary source language")
    parser.add_argument("--memory", default="translation_memory", help="Translation memory folder")
    return parser.parse_args()

def main():
    args = get_args()
    ensure_dirs()
    all_files = sorted(Path(UPLOAD_DIR).glob("*.html"))

    if not all_files:
        print("No HTML files found in uploaded_files/")
        return

    for file in all_files:
        est_size = estimate_html_size(file)
        if est_size > CHARACTER_LIMIT_PRE:
            print(f"Skipping {file.name} – estimated {est_size} chars exceeds pre-extraction limit.")
            continue

        try:
            run_extraction(str(file), args.primary_lang)

            post_char_count = count_json_text_chars("translatable_flat.json")
            if post_char_count > CHARACTER_LIMIT_POST:
                print(f"Skipping {file.name} – extracted JSON has {post_char_count} chars, exceeds limit.")
                continue

            run_translation(
                "translatable_flat.json",
                args.lang,
                args.primary_lang,
                args.secondary_lang,
                args.memory
            )

            file.rename(Path(PROCESSED_DIR) / file.name)
            print(f"✅ Finished: {file.name}")

        except Exception as e:
            print(f"❌ Error processing {file.name}: {str(e)}")

if __name__ == "__main__":
    main()
