#!/usr/bin/env python3
"""
批量处理脚本
自动化执行：剪辑 -> 提取字幕 -> (等待翻译) -> 烧录字幕 -> 生成总结模板
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional

# Import existing scripts
sys.path.append(str(Path(__file__).parent))
from clip_video import clip_video, extract_subtitle_segment, save_subtitles_as_srt
from analyze_subtitles import parse_subtitles
from burn_subtitles import burn_subtitles
from translate_subtitles import create_bilingual_subtitles
from generate_summary import create_chapter_info, generate_summary

def load_chapters(json_path: str) -> List[Dict]:
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_filename(text: str) -> str:
    """清理文件名，移除非法字符"""
    import re
    # 移除 / \ : * ? " < > |
    text = re.sub(r'[\\/:*?"<>|]', '', text)
    # 替换空格为下划线
    text = text.replace(' ', '_')
    return text[:100]  # 限制长度

def process_batch(
    video_path: str,
    subtitle_path: str,
    chapters_json: str,
    output_dir: str,
    skip_translation: bool = False,
    skip_burn: bool = False,
    finalize_only: bool = False
):
    video_path = Path(video_path)
    subtitle_path = Path(subtitle_path)
    chapters_json = Path(chapters_json)
    output_dir = Path(output_dir)

    # --- Directory Auto-Discovery Logic ---
    if video_path.is_dir():
        print(f"🔍 检测到视频输入是目录，尝试自动寻找视频文件...")
        # 优先寻找 mp4, 然后 mkv, webm
        candidates = list(video_path.glob("*.mp4")) + list(video_path.glob("*.mkv")) + list(video_path.glob("*.webm"))
        # 排除掉 clip_ 和 _with_subtitles 的中间文件
        candidates = [c for c in candidates if "_clip" not in c.name and "_with_subtitles" not in c.name]
        
        if candidates:
            video_path = candidates[0]
            print(f"   👉 自动选择视频: {video_path.name}")
        else:
            print(f"   ❌ 错误: 在目录 {video_path} 中未找到视频文件 (.mp4/.mkv)")
            return

    if subtitle_path.is_dir():
        print(f"🔍 检测到字幕输入是目录，尝试自动寻找字幕文件...")
        # 优先寻找 en.vtt (下载的原始字幕), 然后 vtt, srt
        candidates = list(subtitle_path.glob("*.en.vtt")) + list(subtitle_path.glob("*.vtt")) + list(subtitle_path.glob("*.srt"))
        # 排除掉生成的中间字幕
        candidates = [c for c in candidates if "_original" not in c.name and "_translated" not in c.name and "_bilingual" not in c.name]

        if candidates:
            subtitle_path = candidates[0]
            print(f"   👉 自动选择字幕: {subtitle_path.name}")
        else:
            print(f"   ❌ 错误: 在目录 {subtitle_path} 中未找到字幕文件 (.vtt/.srt)")
            return

    if chapters_json.is_dir():
        print(f"🔍 检测到 JSON 输入是目录，尝试自动寻找 chapters.json...")
        potential_json = chapters_json / "chapters.json"
        if potential_json.exists():
            chapters_json = potential_json
            print(f"   👉 自动选择 JSON: {chapters_json.name}")
        else:
            # 尝试寻找任意 json
            candidates = list(chapters_json.glob("*.json"))
            if candidates:
                chapters_json = candidates[0]
                print(f"   ⚠️ 未找到 standard chapters.json，使用: {chapters_json.name}")
            else:
                 print(f"   ❌ 错误: 在目录 {chapters_json} 中未找到 chapters.json")
                 print(f"   💡 提示: 你需要先让 AI 分析字幕并生成章节信息，保存为 'chapters.json'")
                 return
    
    # Check if files exist (Double Check)
    if not video_path.exists():
        print(f"❌ 错误: 视频文件不存在: {video_path}")
        return
    if not subtitle_path.exists():
        print(f"❌ 错误: 字幕文件不存在: {subtitle_path}")
        return
    if not chapters_json.exists():
        print(f"❌ 错误: 章节文件不存在: {chapters_json}")
        print(f"💡 提示: 你需要先让 AI 分析字幕并生成章节信息，保存为 'chapters.json'")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"🚀 开始批量处理...")
    print(f"   视频: {video_path.name}")
    print(f"   字幕: {subtitle_path.name}")
    
    chapters = load_chapters(chapters_json)
    print(f"   章节数: {len(chapters)}")

    # Load full subtitles once
    full_subtitles = parse_subtitles(str(subtitle_path))

    for i, chapter in enumerate(chapters, 1):
        title = chapter.get('title', f'Chapter_{i}')
        start_time = chapter.get('start_time')
        end_time = chapter.get('end_time')
        
        safe_title = clean_filename(title)
        chapter_dir = output_dir / safe_title
        chapter_dir.mkdir(exist_ok=True)
        
        print(f"\n🎬 处理章节 {i}/{len(chapters)}: {title}")
        print(f"   范围: {start_time} - {end_time}")

        # Define file paths
        clip_path = chapter_dir / f"{safe_title}_clip.mp4"
        original_srt_path = chapter_dir / f"{safe_title}_original.srt"
        translated_srt_path = chapter_dir / f"{safe_title}_translated.srt"
        bilingual_srt_path = chapter_dir / f"{safe_title}_bilingual.srt"
        burned_video_path = chapter_dir / f"{safe_title}_with_subtitles.mp4"
        summary_path = chapter_dir / f"{safe_title}_summary.md"

        # --- Phase 1: Preparation (Clip & Extract) ---
        if not finalize_only:
            # 1. Clip Video
            if not clip_path.exists():
                clip_video(
                    video_path=str(video_path),
                    start_time=start_time,
                    end_time=end_time,
                    output_path=str(clip_path)
                )
            else:
                print(f"   ⚠️ 视频片段已存在，跳过剪辑")

            # 2. Extract Subtitles
            if not original_srt_path.exists():
                # Convert time strings to seconds if needed
                from utils import time_to_seconds
                s_sec = time_to_seconds(start_time) if isinstance(start_time, str) else start_time
                e_sec = time_to_seconds(end_time) if isinstance(end_time, str) else end_time
                
                segment_subs = extract_subtitle_segment(full_subtitles, s_sec, e_sec)
                save_subtitles_as_srt(segment_subs, str(original_srt_path))
            else:
                print(f"   ⚠️ 原始字幕已存在，跳过提取")

        # --- Phase 2: Finalization (Burn & Summary) ---
        # Only proceed if we are finalizing OR if we skip translation (meaning we might burn original)
        # But commonly, if we skip translation, we might burn original subs if desired? 
        # For now, let's assume 'finalize' means generating the final artifacts.
        
        if not skip_translation:
             # Check if translated/bilingual subtitles exist
            if bilingual_srt_path.exists():
                subtitle_to_burn = bilingual_srt_path
                print(f"   ✅ 检测到双语字幕")
            elif translated_srt_path.exists():
                # Merge to bilingual if needed (Assume translated SRT is just target lang or bilingual already?)
                # SKILL.md implies we generate bilingual from translated. 
                # For simplicity in batch script, acts as if translated_srt IS the one to use or merge.
                # Let's assume the user/agent provides the 'bilingual' one or 'translated'.
                # To be safe: if bilingual doesn't exist but translated does, maybe we should merge?
                # For this v1 script, let's look for 'bilingual.srt' as the signal to proceed with burning bilingual.
                subtitle_to_burn = translated_srt_path 
                print(f"   ✅ 检测到已翻译字幕")
            else:
                if finalize_only:
                    print(f"   ❌ 未找到翻译字幕 ({bilingual_srt_path.name})，跳过烧录")
                else:
                    print(f"   ⏳ 等待翻译: 请生成 {original_srt_path.name} 的翻译版本")
                subtitle_to_burn = None
        else:
            # If skip translation, maybe burn original?
            subtitle_to_burn = original_srt_path

        # 3. Burn Subtitles
        if not skip_burn and subtitle_to_burn and subtitle_to_burn.exists():
            if not burned_video_path.exists():
                try:
                    burn_subtitles(
                        video_path=str(clip_path),
                        subtitle_path=str(subtitle_to_burn),
                        output_path=str(burned_video_path)
                    )
                except Exception as e:
                    print(f"   ❌ 烧录失败: {e}")
            else:
                print(f"   ⚠️ 烧录视频已存在，跳过")

        # 4. Generate Summary Template
        if not summary_path.exists():
            # Create info for summary
            info = create_chapter_info(
                title=title,
                time_range=f"{start_time} - {end_time}",
                summary=chapter.get('summary', 'Pending'),
                keywords=chapter.get('keywords', [])
            )
            generate_summary(info, str(summary_path))

    print(f"\n✨ 批量处理完成!")
    if not finalize_only and not skip_translation:
        print(f"👉 下一步: 请翻译生成的 subtitle 文件，或运行 --finalize 进行烧录")

def main():
    parser = argparse.ArgumentParser(description="Batch process video chapters")
    parser.add_argument("video_path", help="Input video file path")
    parser.add_argument("subtitle_path", help="Input subtitle file path (VTT/SRT)")
    parser.add_argument("chapters_json", help="Chapters JSON file path")
    parser.add_argument("--output-dir", default="./youtube-clips", help="Output directory")
    parser.add_argument("--skip-translation", action="store_true", help="Skip translation requirement (burn original subs)")
    parser.add_argument("--skip-burn", action="store_true", help="Skip subtitle burning")
    parser.add_argument("--finalize", action="store_true", help="Run finalization (burn & summary) assuming translations exist")

    args = parser.parse_args()

    process_batch(
        args.video_path,
        args.subtitle_path,
        args.chapters_json,
        args.output_dir,
        args.skip_translation,
        args.skip_burn,
        args.finalize
    )

if __name__ == "__main__":
    main()
