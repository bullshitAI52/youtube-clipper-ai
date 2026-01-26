#!/usr/bin/env python3
"""
动态高亮字幕处理器 (Karaoke Mode)
独立工作流：识别(逐字) -> 生成ASS -> 烧录
"""

import os
import sys
import subprocess
from pathlib import Path

# 导入路径
SCRIPT_DIR = Path(__file__).parent
TRANSCRIBE_SCRIPT = SCRIPT_DIR / "transcribe_video.py"
TRANSLATE_SCRIPT = SCRIPT_DIR / "auto_translate_full.py"
GENERATE_ASS_SCRIPT = SCRIPT_DIR / "generate_karaoke_ass.py"
BURN_SCRIPT = SCRIPT_DIR / "burn_subtitles.py"

def process_karaoke(video_path: str, mode: str = 'highlight'):
    video = Path(video_path)
    if not video.exists():
        print(f"❌ 错误: 视频不存在: {video}")
        return

    mode_name = "点读机模式" if mode == 'highlight' else "蹦蹦蹦模式 (跳出)"
    print(f"\n✨ --- 启动动态高亮模式 ({mode_name}) ---")
    print(f"📹 处理视频: {video.name}")

    # 1. AI 语音识别 (生成 JSON 和 SRT)
    json_sub = video.with_suffix(".json")
    if not json_sub.exists():
        print(f"🎙️ 正在进行 AI 逐字识别 (Whisper)...")
        cmd = [sys.executable, str(TRANSCRIBE_SCRIPT), str(video)]
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            print(f"❌ 识别失败: {e}")
            return
    else:
        print(f"✅ 已存在 JSON 数据，跳过识别")

    # 2. 翻译字幕 (生成纯中文 SRT 用于辅助)
    zh_sub = video.with_suffix(".zh_CN.srt")
    if not zh_sub.exists():
        print(f"🌐 正在生成中文翻译...")
        # 使用 auto_translate_full.py 生成模式为 zh 的字幕
        en_srt = video.with_suffix(".en.srt")
        cmd = [sys.executable, str(TRANSLATE_SCRIPT), str(en_srt), "--mode", "zh", "--target", "zh-CN"]
        try:
            subprocess.run(cmd, check=True)
            # auto_translate_full.py 生成文件名逻辑: [en_srt.stem]_zh.srt -> [video.stem].en_zh.srt
            generated_zh = en_srt.with_name(en_srt.stem + "_zh.srt")
            if generated_zh.exists():
                if zh_sub.exists(): os.remove(zh_sub)
                os.rename(generated_zh, zh_sub)
        except Exception as e:
            print(f"⚠️ 翻译失败 (将仅显示英文): {e}")

    # 3. 生成 ASS 特效字幕
    ass_filename = video.stem + f"_{mode}.ass"
    ass_sub = video.parent / ass_filename
    print(f"🎨 正在生成 ASS 特效字幕 ({mode})...")
    
    cmd = [sys.executable, str(GENERATE_ASS_SCRIPT), str(json_sub), str(ass_sub), "False", mode, str(zh_sub)]
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"❌ ASS 生成失败: {e}")
        return

    # 4. 烧录视频
    output_video = video.parent / f"{video.stem}_{mode}.mp4"
    print(f"🔥 正在烧录动态字幕...")
    cmd = [sys.executable, str(BURN_SCRIPT), str(video), str(ass_sub), str(output_video)]
    try:
        subprocess.run(cmd, check=True)
        print(f"\n🎉 搞定！动态视频已生成:")
        print(f"👉 {output_video}")
    except Exception as e:
        print(f"❌ 烧录失败: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python karaoke_processor.py <video_path> [mode]")
        print("Modes: highlight (default), popout")
        sys.exit(1)
    
    mode = sys.argv[2] if len(sys.argv) > 2 else 'highlight'
    process_karaoke(sys.argv[1], mode)

if __name__ == "__main__":
    main()
