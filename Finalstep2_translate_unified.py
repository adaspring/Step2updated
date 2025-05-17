import os
import json
import deepl
import argparse
from pathlib import Path

def create_efficient_translatable_map(
    json_data, 
    translator, 
    target_lang="FR", 
    primary_lang=None, 
    secondary_lang=None, 
    memory_file=None
):
    translation_memory = {}
    if memory_file and os.path.exists(memory_file):
        try:
            with open(memory_file, "r", encoding="utf-8") as f:
                translation_memory = json.load(f)
            print(f"Loaded {len(translation_memory)} cached translations")
        except json.JSONDecodeError:
            print(f"Warning: Corrupted translation memory file {memory_file}")

    translatable_map = {}
    texts_to_translate = []
    token_indices = []
    original_texts = {}

    for block_id, block_data in json_data.items():
        if "text" in block_data:
            text = block_data["text"]
            token = block_id
            if text in translation_memory:
                translatable_map[token] = translation_memory[text]
            else:
                texts_to_translate.append(text)
                token_indices.append(token)
                original_texts[token] = text

        if "segments" in block_data:
            for segment_id, segment_text in block_data["segments"].items():
                token = f"{block_id}_{segment_id}"
                if segment_text in translation_memory:
                    translatable_map[token] = translation_memory[segment_text]
                else:
                    texts_to_translate.append(segment_text)
                    token_indices.append(token)
                    original_texts[token] = segment_text

    if texts_to_translate:
        batch_size = 330
        for batch_idx in range(0, len(texts_to_translate), batch_size):
            batch = texts_to_translate[batch_idx:batch_idx+batch_size]
            translated_batch = []
            try:
                detection_results = translator.translate_text(
                    [text[:100] for text in batch],
                    target_lang=target_lang,
                    preserve_formatting=True
                )

                for idx, detection in enumerate(detection_results):
                    detected_lang = detection.detected_source_lang.lower()
                    allowed_langs = {
                        lang.lower() for lang in [primary_lang, secondary_lang] if lang
                    }
                    text = batch[idx]
                    if allowed_langs and detected_lang in allowed_langs:
                        result = translator.translate_text(text, target_lang=target_lang)
                        translated_batch.append(result.text)
                    else:
                        translated_batch.append(text)
            except Exception as e:
                print(f"Translation skipped for batch (error: {str(e)[:50]}...)")
                translated_batch.extend(batch)

            for j in range(len(batch)):
                global_index = batch_idx + j
                token = token_indices[global_index]
                original_text = original_texts[token]
                final_text = translated_batch[j]
                translatable_map[token] = final_text
                translation_memory[original_text] = final_text

    if memory_file and translation_memory:
        os.makedirs(os.path.dirname(memory_file), exist_ok=True)
        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(translation_memory, f, ensure_ascii=False, indent=2)
        print(f"Updated translation memory with {len(translation_memory)} entries")

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
                return

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

if __name__ == "__main__":
    main()
