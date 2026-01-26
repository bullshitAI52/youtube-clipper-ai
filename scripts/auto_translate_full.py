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
                        help="输出模式: bilingual (双语), zh (纯译文), en (纯原文)")
    parser.add_argument("--target", default='zh-CN', help="目标语言代码 (例如: zh-CN, en, ja)")
    parser.add_argument("--merge", help="已有翻译文件路径 (如果提供，则进行合并而非翻译)")
    parser.add_argument("--reverse", action="store_true", help="双语模式下反转顺序 (原语在上，译文在下)")

    
    args = parser.parse_args()
    vtt_path = Path(args.input_file)
    mode = args.mode
    merge_path = Path(args.merge) if args.merge else None

    if not vtt_path.exists():
        print(f"Error: {vtt_path} not found")
        sys.exit(1)

    print(f"🚀 Loading Subtitle: {vtt_path}")
    
    # 根据模式决定输出文件名
    suffix = f"_{mode}.srt" if mode != 'bilingual' else "_bilingual.srt"
    output_srt = vtt_path.with_name(vtt_path.stem + suffix)
    print(f"📝 Target File: {output_srt} (Mode: {mode})")
    
    target_lang = args.target
    reverse = args.reverse
    
    translator = GoogleTranslator(source='auto', target=target_lang)
    
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

    # 提取所有文本用于翻译
    all_texts = [sub['text'] for sub in valid_subs]

    # Translate in batches to be nice to the API (though GoogleTranslator lib handles some)
    # Let's do batching or just sequential. Sequential is safer for order.
    # deep-translator handles limits? It might throw error if too fast.
    
    # --- 翻译或读取已有翻译 ---
    translated_texts = []
    
    if merge_path and merge_path.exists():
        print(f"🔗 Reading existing translations from: {merge_path}")
        # 简单解析 merge 文件（提取 text）
        with open(merge_path, 'r', encoding='utf-8') as f:
            merge_content = f.read()
            # 移除 VTT 头
            merge_content = re.sub(r'^WEBVTT.*?\n\n', '', merge_content, flags=re.DOTALL)
            merge_blocks = merge_content.strip().split('\n\n')
            for block in merge_blocks:
                m_lines = block.strip().split('\n')
                m_txt = []
                for ml in m_lines:
                    if '-->' not in ml and ml and not ml.isdigit() and 'NOTE' not in ml:
                        m_txt.append(re.sub(r'<[^>]+>', '', ml))
                translated_texts.append(' '.join(m_txt))
        # 补齐长度（如果两个文件行数不一致）
        if len(translated_texts) < len(all_texts):
             translated_texts.extend(all_texts[len(translated_texts):])
    else:
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
            translated = translated_texts[i] if i < len(translated_texts) else original
            
            f.write(f"{i+1}\n")
            f.write(f"{sub['start']} --> {sub['end']}\n")
            
            if mode == 'bilingual':
                if reverse:
                    f.write(f"{original}\n")
                    f.write(f"{translated}\n")
                else:
                    f.write(f"{translated}\n")
                    f.write(f"{original}\n")
            elif mode == 'zh':
                f.write(f"{translated}\n")
            else: # en
                f.write(f"{original}\n")
            f.write("\n")
                
    print(f"\n✅ Done! Subtitles saved to: {output_srt}")

if __name__ == "__main__":
    main()
