#!/usr/bin/env python3
"""
下载 YouTube 视频和字幕
使用 yt-dlp 下载视频（最高 1080p）和英文字幕
"""

import sys
import json
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    print("❌ Error: yt-dlp not installed")
    print("Please install: pip install yt-dlp")
    sys.exit(1)

from utils import (
    validate_url,
    sanitize_filename,
    format_file_size,
    get_video_duration_display,
    ensure_directory
)


def download_video(url: str, output_dir: str = None, only_subs: bool = False, max_height: int = 1080) -> dict:
    """
    下载 YouTube 视频和字幕

    Args:
        url: YouTube URL
        output_dir: 输出目录，默认为当前目录
        only_subs: 是否只下载字幕，不下载视频
        max_height: 最大视频高度，默认 1080

    Returns:
        dict: {
            'video_path': 视频文件路径 (如果不下载视频则为 None),
            'subtitle_path': 字幕文件路径,
            'title': 视频标题,
            'duration': 视频时长（秒）,
            'file_size': 视频文件大小（字节，如果不下载则为 0）
        }

    Raises:
        ValueError: 无效的 URL
        Exception: 下载失败
    """
    # 验证 URL
    if not validate_url(url):
        raise ValueError(f"Invalid YouTube URL: {url}")

    # 设置输出目录
    if output_dir is None:
        output_dir = Path.cwd() / "download"
    else:
        output_dir = Path(output_dir)

    output_dir = ensure_directory(output_dir)

    # 自动识别 FFmpeg 路径
    ffmpeg_path = '/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg' if Path('/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg').exists() else '/usr/local/opt/ffmpeg-full/bin/ffmpeg' if Path('/usr/local/opt/ffmpeg-full/bin/ffmpeg').exists() else 'ffmpeg'

    if only_subs:
        print(f"📄 开始只下载字幕...")
    else:
        print(f"🎬 开始下载视频 (最高 {max_height}p)...")
    print(f"   URL: {url}")
    print(f"   输出目录: {output_dir}")

    # 配置 yt-dlp 选项
    ydl_opts = {
        # 视频格式：不强制下载时的容器格式
        'format': f'bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best',
        'merge_output_format': 'mp4',
        'skip_download': only_subs, # 如果只下载字幕，则跳过视频下载
        
        # SSL 和 网络优化
        'nocheckcertificate': True,
        'retries': 15,
        'fragment_retries': 15,
        'ffmpeg_location': ffmpeg_path,
        
        # 伪装客户端和请求头 (解决 403 和 SABR 问题)
        'http_header': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Sec-Fetch-Mode': 'navigate',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web'],
                'player_skip': ['webpage', 'configs'],
            }
        },

        # 输出模板：包含视频 ID（避免特殊字符问题）
        'outtmpl': str(output_dir / '%(id)s.%(ext)s'),

        # 下载字幕
        'writesubtitles': True,
        'writeautomaticsub': True,  # 自动字幕作为备选
        'subtitleslangs': ['en', 'zh', 'zh-Hans', 'zh-Hant', 'zh-CN', 'zh-TW'], # 尝试下载中英双语
        'subtitlesformat': 'vtt',   # VTT 格式
        
        # 兼容性设置
        'prefer_ffmpeg': True,
        'add_header': [
            'Referer:https://www.google.com/'
        ],

        # 不下载缩略图
        'writethumbnail': False,

        # 静默模式（减少输出）
        'quiet': False,
        'no_warnings': False,

        # 进度钩子
        'progress_hooks': [_progress_hook],
        
        # 忽略错误（防止字幕下载失败导致整个视频下载终止）
        'ignoreerrors': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 一次调用完成信息提取和下载（避免两次网络请求）
            print(f"\n📥 正在获取信息并下载...")
            info = ydl.extract_info(url, download=True)

            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            video_id = info.get('id', 'unknown')

            print(f"   标题: {title}")
            print(f"   时长: {get_video_duration_display(duration)}")
            print(f"   视频ID: {video_id}")

            if not only_subs:
                # 获取下载的文件路径
                video_filename = ydl.prepare_filename(info)
                video_path = Path(video_filename)
                
                # 获取文件大小
                file_size = video_path.stat().st_size if video_path.exists() else 0

                # 验证下载结果
                if not video_path.exists():
                    raise Exception("Video file not found after download")

                print(f"\n✅ 视频下载完成: {video_path.name}")
                print(f"   大小: {format_file_size(file_size)}")
            else:
                # 只下载字幕的情况
                video_path = None
                file_size = 0
                print(f"\n✅ 视频信息获取完成 (已跳过下载)")

            # 优先查找英文字幕作为原始源
            subtitle_path = None
            zh_subtitle_path = None
            
            # ydl.prepare_filename 即使在 skip_download=True 也会给出预期的 mp4 路径
            expected_video_path = Path(ydl.prepare_filename(info))
            
            # 查找所有可能的字幕文件
            all_subs = list(expected_video_path.parent.glob(f"{expected_video_path.stem}.*vtt"))
            for sub in all_subs:
                if '.en.' in sub.name:
                    subtitle_path = sub
                elif any(lang in sub.name for lang in ['.zh.', '.zh-Hans.', '.zh-CN.', '.zh-Hant.', '.zh-TW.']):
                    zh_subtitle_path = sub

            # 如果没找到带语言标签的，尝试默认后缀
            if not subtitle_path and expected_video_path.with_suffix('.vtt').exists():
                subtitle_path = expected_video_path.with_suffix('.vtt')

            if subtitle_path and subtitle_path.exists():
                print(f"✅ 英文字幕下载完成: {subtitle_path.name}")
            if zh_subtitle_path and zh_subtitle_path.exists():
                print(f"✅ 中文字幕下载完成: {zh_subtitle_path.name}")
            
            if not subtitle_path and not zh_subtitle_path:
                print(f"⚠️  未找到任何字幕")
                print(f"   提示：某些视频可能没有字幕或需要自动生成")

            return {
                'video_path': str(video_path) if video_path else None,
                'subtitle_path': str(subtitle_path) if subtitle_path else None,
                'zh_subtitle_path': str(zh_subtitle_path) if zh_subtitle_path else None,
                'title': title,
                'duration': duration,
                'file_size': file_size,
                'video_id': video_id
            }

    except Exception as e:
        print(f"\n❌ 下载失败: {str(e)}")
        raise


def _progress_hook(d):
    """下载进度回调"""
    if d['status'] == 'downloading':
        # 显示下载进度
        if 'downloaded_bytes' in d and 'total_bytes' in d and d['total_bytes']:
            percent = d['downloaded_bytes'] / d['total_bytes'] * 100
            downloaded = format_file_size(d['downloaded_bytes'])
            total = format_file_size(d['total_bytes'])
            speed = d.get('speed', 0)
            speed_str = format_file_size(speed) + '/s' if speed else 'N/A'

            # 使用 \r 实现进度条覆盖
            bar_length = 30
            filled = int(bar_length * percent / 100)
            bar = '█' * filled + '░' * (bar_length - filled)

            print(f"\r   [{bar}] {percent:.1f}% - {downloaded}/{total} - {speed_str}", end='', flush=True)
        elif 'downloaded_bytes' in d:
            # 无总大小信息时，只显示已下载
            downloaded = format_file_size(d['downloaded_bytes'])
            speed = d.get('speed', 0)
            speed_str = format_file_size(speed) + '/s' if speed else 'N/A'
            print(f"\r   下载中... {downloaded} - {speed_str}", end='', flush=True)

    elif d['status'] == 'finished':
        print()  # 换行


def main():
    import argparse
    parser = argparse.ArgumentParser(description="下载 YouTube 视频和字幕")
    parser.add_argument("url", help="YouTube URL")
    parser.add_argument("output_dir", nargs="?", default=None, help="输出目录")
    parser.add_argument("--only-subs", action="store_true", help="只下载字幕")
    parser.add_argument("--max-height", type=int, default=1080, help="最高视频高度 (默认 1080)")
    
    args = parser.parse_args()

    try:
        result = download_video(args.url, args.output_dir, args.only_subs, args.max_height)

        # 输出 JSON 结果（供其他脚本使用）
        print("\n" + "="*60)
        print("下载结果 (JSON):")
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
