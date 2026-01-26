#!/usr/bin/env python3
import sys
import os
from pathlib import Path
from deep_translator import GoogleTranslator

from datetime import timedelta

def vtt_timestamp_to_srt(timestamp):
    # webvtt timestamp: 00:00:13.120
    # srt timestamp: 00:00:13,120
    return timestamp.replace('.', ',')

def seconds_to_srt_time(seconds):
    td = timedelta(seconds=seconds)
    # format: HH:MM:SS,mmm
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int(td.microseconds / 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

def main():
    import argparse
    parser = argparse.ArgumentParser(description="自动翻译 VTT/SRT 字幕")
    parser.add_argument("input_file", help="输入的字幕文件路径 (VTT 或 SRT)")
    parser.add_argument("--mode", choices=['bilingual', 'zh', 'en'], default='bilingual', 
                        help="输出模式: bilingual (双语), zh (纯中文), en (纯英文)")
    
    args = parser.parse_args()
    vtt_path = Path(args.input_file)
    mode = args.mode

    if not vtt_path.exists():
        print(f"Error: {vtt_path} not found")
        sys.exit(1)

    print(f"🚀 Loading Subtitle: {vtt_path}")
    
    # 根据模式决定输出文件名
    suffix = f"_{mode}.srt" if mode != 'bilingual' else "_bilingual.srt"
    output_srt = vtt_path.with_name(vtt_path.stem + suffix)
    print(f"📝 Target File: {output_srt} (Mode: {mode})")
    
    translator = GoogleTranslator(source='auto', target='zh-CN')
    
    import re
    
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove header
    content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.DOTALL)
    blocks = content.strip().split('\n\n')
    
    valid_subs = []
    
    print(f"   Found {len(blocks)} blocks. Processing...")
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2: continue
        
        timestamp_line = None
        text_lines = []
        
        for line in lines:
            if '-->' in line:
                timestamp_line = line
            elif line and not line.isdigit() and 'NOTE' not in line:
                text_lines.append(line)
        
        if not timestamp_line or not text_lines:
            continue
            
        # Parse timestamp
        # 00:00:13.120 --> 00:00:17.536 align:start position:0%
        times = timestamp_line.split('-->')
        start = times[0].strip().split(' ')[0]
        end = times[1].strip().split(' ')[0]
        
        # Convert to SRT format (dot to comma)
        start_srt = start.replace('.', ',')
        end_srt = end.replace('.', ',')
        
        text = ' '.join(text_lines)
        # Clean tags
        text = re.sub(r'<[^>]+>', '', text)
        
        valid_subs.append({
            'start': start_srt,
            'end': end_srt,
            'text': text
        })

    # Translate in batches to be nice to the API (though GoogleTranslator lib handles some)
    # Let's do batching or just sequential. Sequential is safer for order.
    # deep-translator handles limits? It might throw error if too fast.
    
    # Prepare texts
    all_texts = [sub['text'] for sub in valid_subs]
    translated_texts = []
    
    # Batch size (Google URL limits)
    BATCH_SIZE = 20
    
    print(f"🔄 Starting batch translation (Batch size: {BATCH_SIZE})...")
    
    for i in range(0, len(all_texts), BATCH_SIZE):
        batch = all_texts[i:i+BATCH_SIZE]
        try:
            results = translator.translate_batch(batch)
            translated_texts.extend(results)
            print(f"   Processed {min(i+BATCH_SIZE, len(all_texts))}/{len(all_texts)} lines...", end='\r')
        except Exception as e:
            print(f"\n⚠️ Batch translation failed at index {i}: {e}")
            # Fallback to original for this batch
            translated_texts.extend(batch)

    print("\n✅ Translation complete. Writing SRT...")

    with open(output_srt, 'w', encoding='utf-8') as f:
        for i, sub in enumerate(valid_subs):
            original = sub['text']
            chinese = translated_texts[i] if i < len(translated_texts) else original
            
            f.write(f"{i+1}\n")
            f.write(f"{sub['start']} --> {sub['end']}\n")
            
            if mode == 'bilingual':
                f.write(f"{chinese}\n")
                f.write(f"{original}\n")
            elif mode == 'zh':
                f.write(f"{chinese}\n")
            else: # en
                f.write(f"{original}\n")
            f.write("\n")
                
    print(f"\n✅ Done! Subtitles saved to: {output_srt}")

if __name__ == "__main__":
    main()
