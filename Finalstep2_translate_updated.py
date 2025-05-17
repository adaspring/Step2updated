import os
import json
import deepl
import argparse
from pathlib import Path

# (Functions remain unchanged: create_efficient_translatable_map, translate_json_file, apply_translations)

def create_efficient_translatable_map(
    json_data, 
    translator, 
    target_lang="FR", 
    primary_lang=None, 
    secondary_lang=None, 
    memory_file=None
):
    # ... [no change to this function]
    # (Truncated here for brevity – you already have the full function)

    return translatable_map

def translate_json_file(
    input_file, 
    output_file, 
    target_lang="FR", 
    primary_lang=None, 
    secondary_lang=None, 
    memory_dir="translation_memory",
    segment_file=None
):
    auth_key = os.getenv("DEEPL_AUTH_KEY")
    if not auth_key:
        raise ValueError("DEEPL_AUTH_KEY environment variable not set")

    translator = deepl.Translator(auth_key)
    
    os.makedirs(memory_dir, exist_ok=True)
    memory_file = os.path.join(memory_dir, f"translation_memory_{target_lang.lower()}.json")

    with open(input_file, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    translatable_map = create_efficient_translatable_map(
        json_data=json_data,
        translator=translator,
        target_lang=target_lang,
        primary_lang=primary_lang,
        secondary_lang=secondary_lang,
        memory_file=memory_file
    )

    translated_data = {}
    for block_id, block_data in json_data.items():
        translated_block = block_data.copy()
        if "text" in block_data:
            translated_block["text"] = translatable_map.get(block_id, block_data["text"])
        if "segments" in block_data:
            translated_block["segments"] = {
                seg_id: translatable_map.get(f"{block_id}_{seg_id}", seg_text)
                for seg_id, seg_text in block_data["segments"].items()
            }
        translated_data[block_id] = translated_block

    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(translated_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Translation completed: {output_file}")

    if segment_file:
        segment_translations = {}
        for block_id, block_data in translated_data.items():
            if "segments" in block_data:
                for seg_id, seg_text in block_data["segments"].items():
                    segment_translations[seg_id] = seg_text

        with open(segment_file, "w", encoding="utf-8") as f:
            json.dump(segment_translations, f, indent=2, ensure_ascii=False)
        print(f"✅ Segment-only translations exported: {segment_file}")

    return translated_data

def apply_translations(original_file, translations_file, output_file):
    with open(original_file, "r", encoding="utf-8") as f:
        original_data = json.load(f)
    with open(translations_file, "r", encoding="utf-8") as f:
        translations = json.load(f)

    translated_data = {}
    for block_id, block_data in original_data.items():
        translated_block = block_data.copy()
        if "text" in block_data:
            translated_block["text"] = translations.get(block_id, block_data["text"])
        if "segments" in block_data:
            translated_block["segments"] = {
                seg_id: translations.get(f"{block_id}_{seg_id}", seg_text)
                for seg_id, seg_text in block_data["segments"].items()
            }
        translated_data[block_id] = translated_block

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(translated_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Applied translations to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Translate JSON content with language validation")
    parser.add_argument("--input", "-i", default="translatable_flat.json", help="Input JSON file")
    parser.add_argument("--output", "-o", default="translations.json", help="Output JSON file")
    parser.add_argument("--lang", "-l", required=True, help="Target language code (e.g., FR, ES)")
    parser.add_argument("--primary-lang", help="Primary source language code (from step1)")
    parser.add_argument("--secondary-lang", help="Secondary source language code (from step1)")
    parser.add_argument("--memory", "-m", default="translation_memory", help="Translation memory directory")
    parser.add_argument("--apply", "-a", action="store_true", help="Apply translations to original structure")
    parser.add_argument("--segments", "-s", help="Output file for segment-only translations")
    parser.add_argument("--skip-if-cached", action="store_true", help="Skip translation if all text blocks are found in memory")

    args = parser.parse_args()

    if args.skip_if_cached:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                data = json.load(f)

            memory_path = os.path.join(args.memory, f"translation_memory_{args.lang}.json")
            memory = {}
            if os.path.exists(memory_path):
                with open(memory_path, "r", encoding="utf-8") as mf:
                    memory = json.load(mf)

            all_cached = True
            for block in data.values():
                texts = []
                if "text" in block:
                    texts.append(block["text"])
                if "segments" in block:
                    texts.extend(block["segments"].values())
                if any(t not in memory for t in texts):
                    all_cached = False
                    break

            if all_cached:
                print("✅ All text blocks found in memory. Skipping API translation.")
                translated_data = {}
                for block_id, block in data.items():
                    translated = block.copy()
                    if "text" in block:
                        translated["text"] = memory.get(block["text"], block["text"])
                    if "segments" in block:
                        translated["segments"] = {
                            seg_id: memory.get(seg_text, seg_text)
                            for seg_id, seg_text in block["segments"].items()
                        }
                    translated_data[block_id] = translated

                with open(args.output, "w", encoding="utf-8") as out:
                    json.dump(translated_data, out, ensure_ascii=False, indent=2)
                print(f"✅ Translated file written from memory to {args.output}")
                exit(0)

        except Exception as e:
            print(f"⚠️ Error during memory check. Falling back to normal translation: {e}")

    try:
        translations = translate_json_file(
            input_file=args.input,
            output_file=args.output,
            target_lang=args.lang,
            primary_lang=args.primary_lang,
            secondary_lang=args.secondary_lang,
            memory_dir=args.memory,
            segment_file=args.segments
        )

        if args.apply:
            apply_translations(args.input, args.output, f"translated_{args.input}")

    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)

    exit(0)

if __name__ == "__main__":
    main()