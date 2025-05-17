import os
import json
import subprocess
from pathlib import Path

# Configuration
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

def run_translation(json_path, lang, primary_lang, secondary_lang):
    print(f"Running translation for {json_path}")
    command = [
        "python", "Finalstep2_translate.py",
        "--input", json_path,
        "--output", "translations.json",
        "--lang", lang,
        "--primary-lang", primary_lang,
        "--memory", "translation_memory",
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

def prompt_user_file_selection(html_files):
    print("Available HTML files:")
    for idx, file in enumerate(html_files, start=1):
        print(f"{idx}. {file.name}")
    choice = input("Enter file numbers to process (e.g., 1,3,5) or 'all' to process all: ").strip()
    if choice.lower() == "all":
        return html_files
    else:
        selected_indices = {int(i.strip()) for i in choice.split(",") if i.strip().isdigit()}
        return [html_files[i - 1] for i in selected_indices if 0 < i <= len(html_files)]

def main(lang="en", primary_lang="en", secondary_lang=None):
    ensure_dirs()
    all_files = sorted(Path(UPLOAD_DIR).glob("*.html"))

    if not all_files:
        print("No HTML files found in uploaded_files/")
        return

    selected_files = prompt_user_file_selection(all_files)

    for file in selected_files:
        est_size = estimate_html_size(file)
        if est_size > CHARACTER_LIMIT_PRE:
            print(f"Skipping {file.name} – estimated {est_size} chars exceeds pre-extraction limit.")
            continue

        try:
            run_extraction(str(file), lang)

            post_char_count = count_json_text_chars("translatable_flat.json")
            if post_char_count > CHARACTER_LIMIT_POST:
                print(f"Skipping {file.name} – extracted JSON has {post_char_count} chars, exceeds limit.")
                continue

            run_translation("translatable_flat.json", lang, primary_lang, secondary_lang)

            file.rename(Path(PROCESSED_DIR) / file.name)
            print(f"✅ Finished: {file.name}")

        except Exception as e:
            print(f"❌ Error processing {file.name}: {str(e)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Interactive Batch HTML translation manager.")
    parser.add_argument("--lang", required=True, help="spaCy language code (e.g., en, zh, fr)")
    parser.add_argument("--primary-lang", required=True, help="Primary source language for translation")
    parser.add_argument("--secondary-lang", help="Secondary source language for translation (optional)")
    args = parser.parse_args()

    main(args.lang, args.primary_lang, args.secondary_lang)