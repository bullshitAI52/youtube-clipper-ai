#!/usr/bin/env python3
"""
使用 OpenAI Whisper 转录视频音频并生成字幕 (SRT)
"""

import sys
import os
from pathlib import Path
import json

def format_timestamp(seconds: float) -> str:
    """将秒数转换为 SRT 时间戳格式 (HH:MM:SS,mmm)"""
    td = float(seconds)
    hours = int(td // 3600)
    minutes = int((td % 3600) // 60)
    secs = int(td % 60)
    millis = int((td - int(td)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

import subprocess
import shutil

def transcribe_video(video_path: str, model_name: str = "base", output_path: str = None):
    """使用系统安装的 whisper 命令转录视频"""
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Error: Video file not found: {video_path}")
        return None

    # 寻找 whisper 命令
    whisper_cmd = shutil.which("whisper")
    if not whisper_cmd:
        # 尝试常用路径
        common_paths = ["/opt/homebrew/bin/whisper", "/usr/local/bin/whisper"]
        for p in common_paths:
            if Path(p).exists():
                whisper_cmd = p
                break
    
    if not whisper_cmd:
        print("❌ Error: 'whisper' command not found in PATH.")
        print("Please ensure whisper is installed (e.g., brew install whisper or pip install openai-whisper)")
        return None

    if output_path is None:
        output_dir = video_path.parent
        output_path = video_path.with_suffix(".en.srt")
    else:
        output_path = Path(output_path)
        output_dir = output_path.parent

    print(f"🚀 开始转录视频: {video_path.name}")
    print(f"   使用命令: {whisper_cmd}")
    print(f"   使用模型: {model_name}")
    
    # 构建命令
    cmd = [
        whisper_cmd,
        str(video_path),
        "--model", model_name,
        "--output_format", "all",  # 生成所有格式（包括 json, srt）以便后续解析
        "--output_dir", str(output_dir),
        "--language", "English"
    ]
    
    # 启用逐字时间戳（如果可用）
    cmd.extend(["--word_timestamps", "True"])
    
    # 设置包含 FFmpeg 的环境变量
    env = os.environ.copy()
    ffmpeg_extra_path = "/opt/homebrew/opt/ffmpeg-full/bin"
    if ffmpeg_extra_path not in env.get("PATH", ""):
        env["PATH"] = f"{ffmpeg_extra_path}:{env.get('PATH', '')}"

    print(f"   正在转录（这可能需要几分钟）...")
    try:
        # 直接运行命令
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        if result.returncode != 0:
            print(f"❌ Whisper command failed with exit code {result.returncode}")
            print(f"Stderr: {result.stderr}")
            return None

        # Whisper 默认生成的命名是 [video_stem].[lang].srt（如 video.en.srt）
        # 同时也兼容 [video_stem].srt 的旧版格式
        generated_file = output_dir / f"{video_path.stem}.en.srt"
        if not generated_file.exists():
            generated_file = output_dir / f"{video_path.stem}.srt"
        
        if generated_file.exists():
            # 重命名为预期的 .en.srt 避免混乱
            if generated_file != output_path:
                if output_path.exists(): os.remove(output_path)
                shutil.move(str(generated_file), str(output_path))
            print(f"✅ 转录完成！字幕已保存至: {output_path}")
            return str(output_path)
        else:
            print(f"⚠️  警告: 转录结束但未找到预期的输出文件: {generated_file}")
            return None
        
    except Exception as e:
        print(f"❌ Error during transcription: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python transcribe_video.py <video_path> [model_name]")
        print("Example: python transcribe_video.py video.mp4 base")
        sys.exit(1)

    video_path = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else "base"
    
    transcribe_video(video_path, model_name)

if __name__ == "__main__":
    main()
