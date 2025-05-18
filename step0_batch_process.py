
import os
import subprocess
from pathlib import Path

UPLOAD_DIR = Path("upload_files")
OUTPUT_DIR = Path("output")
LANG_PRIMARY = "en"
LANG_SECONDARY = "fr"
TARGET_LANG = "FR"
MEMORY_DIR = "translation_memory"

def run_step1(input_path):
    subprocess.run([
        "python", "Finalstep1_extract.py",
        str(input_path),
        "--lang", LANG_PRIMARY
    ], check=True)

def run_step2(flat_json_path, output_path):
    subprocess.run([
        "python", "Finalstep2_translate.py",
        "--input", str(flat_json_path),
        "--output", str(output_path / "translations.json"),
        "--lang", TARGET_LANG,
        "--primary-lang", LANG_PRIMARY,
        "--secondary-lang", LANG_SECONDARY,
        "--memory", MEMORY_DIR,
        "--apply",
        "--segments", str(output_path / "segments.json")
    ], check=True)

def move_step1_outputs(output_path):
    for filename in [
        "translatable_flat.json",
        "translatable_structured.json",
        "translatable_flat_sentences.json",
        "non_translatable.html"
    ]:
        src = Path(filename)
        if src.exists():
            src.rename(output_path / filename)

def main():
    if not UPLOAD_DIR.exists():
        print(f"Upload folder {UPLOAD_DIR} not found.")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    Path(MEMORY_DIR).mkdir(exist_ok=True)

    html_files = list(UPLOAD_DIR.glob("*.html"))
    if not html_files:
        print("No HTML files found in upload_files.")
        return

    for html_file in html_files:
        print(f"Processing {html_file.name}...")
        file_stem = html_file.stem
        output_path = OUTPUT_DIR / file_stem
        output_path.mkdir(parents=True, exist_ok=True)

        # Step 1: Extract
        run_step1(html_file)
        move_step1_outputs(output_path)

        # Step 2: Translate
        flat_json_path = output_path / "translatable_flat.json"
        run_step2(flat_json_path, output_path)

    print("✅ Batch processing complete.")

if __name__ == "__main__":
    main()
