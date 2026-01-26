#!/usr/bin/env python3
"""
批量处理本地视频：识别 -> 翻译 -> 烧录
针对放置在 download 文件夹中的视频文件进行全自动处理
"""

import os
import sys
from pathlib import Path
import subprocess

# 导入现有脚本路径
SCRIPT_DIR = Path(__file__).parent
TRANSCRIBE_SCRIPT = SCRIPT_DIR / "transcribe_video.py"
TRANSLATE_SCRIPT = SCRIPT_DIR / "auto_translate_full.py"
BURN_SCRIPT = SCRIPT_DIR / "burn_subtitles.py"

def process_local_folder(folder_path: str, mode: str = 'bilingual'):
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        print(f"❌ 错误: 目录不存在: {folder}")
        return

    # 1. 寻找视频文件 (排除已经烧录过的)
    video_extensions = [".mp4", ".mkv", ".webm"]
    videos = [f for f in folder.glob("*") if f.suffix.lower() in video_extensions and "_burned" not in f.name and "_clip" not in f.name]

    if not videos:
        print(f" folder {folder} 中没有发现待处理的视频文件。")
        return

    print(f"🔍 发现 {len(videos)} 个视频，准备开始批量加字幕流程...")

    for i, video in enumerate(videos, 1):
        print(f"\n--- [{i}/{len(videos)}] 正在处理: {video.name} ---")
        
        # A. 检查/生成字幕
        # 寻找同名或 .en.vtt / .en.srt / .srt
        expected_subs = [
            video.with_suffix(".en.vtt"),
            video.with_suffix(".vtt"),
            video.with_suffix(".en.srt"),
            video.with_suffix(".srt")
        ]
        
        original_sub = None
        for s in expected_subs:
            if s.exists():
                original_sub = s
                break
        
        if not original_sub:
            print(f"🎙️ 未发现字幕文件，启动 AI 语音转文字 (Whisper)...")
            # 调用 transcribe_video.py
            cmd = [sys.executable, str(TRANSCRIBE_SCRIPT), str(video)]
            try:
                subprocess.run(cmd, check=True)
                # 转录后应该生成了 .en.srt
                original_sub = video.with_suffix(".en.srt")
            except Exception as e:
                print(f"❌ 转录失败: {e}")
                continue

        if not original_sub or not original_sub.exists():
            print(f"❌ 无法获取字幕，跳过此视频。")
            continue

        # B. 翻译/转换字幕 (生成指定模式的 srt)
        suffix = f"_{mode}.srt" if mode != 'bilingual' else "_bilingual.srt"
        target_sub = video.with_suffix(suffix)
        
        if not target_sub.exists():
            print(f"🌐 正在生成字幕文件 (模式: {mode})...")
            cmd = [sys.executable, str(TRANSLATE_SCRIPT), str(original_sub), "--mode", mode]
            try:
                subprocess.run(cmd, check=True)
            except Exception as e:
                print(f"❌ 字幕转换失败: {e}")
                continue
        else:
            print(f"✅ 已存在目标字幕: {target_sub.name}")

        # C. 烧录字幕
        output_video = video.parent / f"{video.stem}_burned_{mode}.mp4"
        if not output_video.exists():
            print(f"🔥 正在烧录字幕到视频...")
            cmd = [sys.executable, str(BURN_SCRIPT), str(video), str(target_sub), str(output_video)]
            try:
                subprocess.run(cmd, check=True)
                print(f"✨ 成功生成: {output_video.name}")
            except Exception as e:
                print(f"❌ 烧录失败: {e}")
        else:
            print(f"✅ 烧录视频已存在: {output_video.name}")

    print(f"\n🎉 所有本地视频处理完成！")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="批量处理本地视频：识别 -> 翻译 -> 烧录")
    parser.add_argument("folder", nargs="?", default="./download", help="视频所在目录")
    parser.add_argument("--mode", choices=['bilingual', 'zh', 'en'], default='bilingual', 
                        help="字幕模式: bilingual (双语), zh (纯中), en (纯英)")
    
    args = parser.parse_args()
    process_local_folder(args.folder, args.mode)

if __name__ == "__main__":
    main()
