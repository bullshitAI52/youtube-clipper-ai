#!/usr/bin/env python3
"""
将 Whisper 输出的 JSON (包含逐字时间戳) 转换为 ASS 特效字幕 (Karaoke)
"""

import json
import sys
import os
from pathlib import Path

def format_ass_time(seconds: float) -> str:
    """将秒数转换为 ASS 时间格式 (H:MM:SS.cc)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"

def load_secondary_subs(srt_path: str):
    """更稳健地解析 SRT 文件用于提取文本"""
    if not srt_path or not os.path.exists(srt_path):
        print(f"⚠️  未找到辅助字幕文件: {srt_path}")
        return []
    
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read().replace('\r\n', '\n').strip()
    except Exception as e:
        print(f"⚠️  读取辅助字幕失败: {e}")
        return []
    
    # 使用正则表达式匹配 SRT 块
    import re
    # 匹配模式：数字、时间轴、内容
    # 这里的正则表达式处理了多行内容直到双换行或文件结束
    blocks = re.split(r'\n\n+', content)
    subs = []
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            # 跳过序号和时间轴，合并后续所有行
            text = " ".join(lines[2:])
            subs.append(text)
    
    print(f"📖  从 {os.path.basename(srt_path)} 加载了 {len(subs)} 条文本")
    return subs

def generate_ass(json_path: str, output_path: str, is_vertical: bool = False, mode: str = 'highlight', secondary_srt: str = None):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    secondary_texts = load_secondary_subs(secondary_srt) if secondary_srt else []

    # ASS Header
    ass_content = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    ]

    # 样式配置
    font_size = 60 if not is_vertical else 45
    secondary_font_size = int(font_size * 1.2) # 中文放大约2倍，使其清晰可见
    margin_v = 150 if not is_vertical else 400 # 增加基础边距，给两行留空间
    
    # PrimaryColour: 白色 (&H00FFFFFF) 或 透明 (&HFF000000)
    # SecondaryColour: 黄色 (&H0000FFFF) - 用于 Karaoke 高亮状态
    primary_color = "&H00FFFFFF" if mode == 'highlight' else "&HFF000000"
    
    # 定义标准样式 (Layer 1) 和翻译样式 (Layer 0)
    # Alignment 2 是底部居中
    ass_content.append(f"Style: Default,Arial,{font_size},{primary_color},&H0000FFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,1,2,20,20,{margin_v},1")
    ass_content.append(f"Style: Secondary,Arial,{secondary_font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,2,20,20,{margin_v - int(secondary_font_size * 1.2)},1")
    
    ass_content.extend([
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ])

    for i, segment in enumerate(data.get('segments', [])):
        start_time = format_ass_time(segment['start'])
        end_time = format_ass_time(segment['end'])
        
        words_parts = []
        last_word_end = segment['start']
        
        for word_data in segment.get('words', []):
            word_text = word_data['word']
            w_start = word_data['start']
            w_end = word_data['end']
            
            # 计算前缀静默/间隙
            gap_duration = int((w_start - last_word_end) * 100)
            if gap_duration > 0:
                words_parts.append(f"{{\\k{gap_duration}}}")
            
            # 计算单词持续时间 (单位: 厘秒 1/100s)
            duration = int((w_end - w_start) * 100)
            if duration <= 0: duration = 1 # 防止为0
            
            words_parts.append(f"{{\\k{duration}}}{word_text}")
            last_word_end = w_end
            
        line_text = "".join(words_parts)
        # 第一层：主要的动态字幕 (英文)
        ass_content.append(f"Dialogue: 1,{start_time},{end_time},Default,,0,0,0,,{line_text}")
        
        # 第二层：次要的静态字幕 (中文)
        if i < len(secondary_texts):
            trans_text = secondary_texts[i]
            # 如果是 popout 模式，中文可以设置淡入或者稍微延后，但这里为简单起见保持同步静态显示
            ass_content.append(f"Dialogue: 0,{start_time},{end_time},Secondary,,0,0,0,,{trans_text}")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(ass_content))
    
    print(f"✅ ASS 字幕已生成: {output_path}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_karaoke_ass.py <json_path> <output_path> [is_vertical] [mode] [secondary_srt]")
        print("Modes: highlight (default), popout")
        sys.exit(1)
    
    json_path = sys.argv[1]
    output_path = sys.argv[2]
    is_vertical = sys.argv[3].lower() == 'true' if len(sys.argv) > 3 else False
    mode = sys.argv[4] if len(sys.argv) > 4 else 'highlight'
    secondary_srt = sys.argv[5] if len(sys.argv) > 5 else None
    
    generate_ass(json_path, output_path, is_vertical, mode, secondary_srt)

if __name__ == "__main__":
    main()
