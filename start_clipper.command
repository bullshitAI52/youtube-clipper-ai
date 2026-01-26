#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}   YouTube Clipper 自动化助手             ${NC}"
echo -e "${GREEN}==========================================${NC}"

# 获取当前脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"  # 关键：切换到脚本所在目录，确保相对路径正确

BATCH_SCRIPT="$SCRIPT_DIR/scripts/batch_processor.py"
DOWNLOAD_SCRIPT="$SCRIPT_DIR/scripts/download_video.py"
TRANSCRIBE_SCRIPT="$SCRIPT_DIR/scripts/transcribe_video.py"
LOCAL_BATCH_SCRIPT="$SCRIPT_DIR/scripts/process_local_folder.py"
KARAOKE_SCRIPT="$SCRIPT_DIR/scripts/karaoke_processor.py"
OUTPUT_ROOT="$SCRIPT_DIR/download"

# 确保能找到 pip 安装的包
# 1. 硬编码已知的 macOS Python 3.9 用户包路径
export PYTHONPATH="/Users/apple/Library/Python/3.9/lib/python/site-packages:$PYTHONPATH"
# 2. 动态添加当前 python 的用户包路径
export PYTHONPATH=$PYTHONPATH:$(python3 -c "import site; print(site.getusersitepackages())")
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

# Self-Check & Auto-Repair
echo "Checking environment..."
# 强制更新 yt-dlp 并安装防检测组件 curl-cffi
echo "Updating dependencies (yt-dlp, curl-cffi)..."
python3 -m pip install -U yt-dlp "curl-cffi>=0.5.10" 2>/dev/null

python3 -c "import yt_dlp" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  检测到 yt-dlp 缺失，正在尝试自动修复...${NC}"
    echo "Running: python3 -m pip install yt-dlp curl-cffi"
    python3 -m pip install yt-dlp curl-cffi
    
    # Re-check
    python3 -c "import yt_dlp" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 自动修复失败。请尝试手动运行: python3 -m pip install yt-dlp curl-cffi${NC}"
    else
        echo -e "${GREEN}✅ 修复成功！${NC}"
    fi
fi

# Debug Info
echo "Working Directory: $(pwd)"
echo "Python: $(which python3)"
echo "PYTHONPATH: $PYTHONPATH"

while true; do
    echo -e "\n${CYAN}请选择操作模式:${NC}"
    echo "1. 📥 下载视频 (YouTube -> MP4 + VTT)"
    echo "2. 📄 只下字幕 (Skip Video)"
    echo "3. 🎙️  AI 转录 (针对无字幕视频: MP4 -> SRT)"
    echo "4. 🚀 批量加字幕 (本地 download 文件夹 -> 双语视频)"
    echo "5. ✂️  一键处理 (准备: 剪辑 + 提取)"
    echo "6. 🔥 一键终结 (烧录: 字幕 + 输出)"
    echo "7. ✨ 动态高亮模式 (点读机效果)"
    echo "8. 🎬 蹦蹦蹦模式 (逐字跳出效果)"
    echo "9. 🚪 退出"

    read -p "请输入选项 (1-9) 或直接粘贴 YouTube 链接: " choice

    # 如果输入的是链接（包含 http），自动切换到下载模式
    if [[ $choice == *"http"* ]]; then
        url=$choice
        choice="1"
    fi

    if [[ $choice == "1" ]]; then
        echo -e "\n${YELLOW}--- 模式 1: 下载视频 ---${NC}"
        
        # 如果刚才没有直接输入链接，则现在询问
        if [[ -z "$url" ]]; then
            echo "请输入 YouTube 链接:"
            read -e url
        fi
        
        # 去除额外的引号
        url=${url//\'/}
        url=${url//\"/}
        
        echo -e "\n${CYAN}选择质量 (回车默认 1080p):${NC}"
        echo "1. 2160p (4K)"
        echo "2. 1440p (2K)"
        echo "3. 1080p"
        echo "4. 720p"
        read -p "请输入选项 (1-4): " q_choice
        
        max_h=1080
        case $q_choice in
            1) max_h=2160 ;;
            2) max_h=1440 ;;
            3) max_h=1080 ;;
            4) max_h=720 ;;
        esac

        echo -e "\n${GREEN}🚀 开始下载...${NC}"
        echo "最高高度: ${max_h}p"
        echo "保存目录: $OUTPUT_ROOT"
        
        python3 "$DOWNLOAD_SCRIPT" "$url" "$OUTPUT_ROOT" --max-height "$max_h"
        
        if [ $? -eq 0 ]; then
            echo -e "\n${GREEN}✅ 下载完成！${NC}"
            echo -e "文件保存在: ${CYAN}$OUTPUT_ROOT${NC}"
        else
            echo -e "\n${RED}❌ 下载失败，请检查上方错误信息。${NC}"
        fi
        
        # 重置 url 变量，以免影响下一次循环
        url=""
        
        echo -e "\n按回车键返回主菜单..."
        read

    elif [[ $choice == "2" ]]; then
        echo -e "\n${YELLOW}--- 模式 2: 只下载字幕 ---${NC}"
        echo "请输入 YouTube 链接:"
        read -e url
        url=${url//\'/}
        url=${url//\"/}
        
        echo -e "\n${GREEN}🚀 开始提取字幕...${NC}"
        python3 "$DOWNLOAD_SCRIPT" "$url" "$OUTPUT_ROOT" --only-subs
        
        if [ $? -eq 0 ]; then
            echo -e "\n${GREEN}✅ 字幕获取完成！${NC}"
        else
            echo -e "\n${RED}❌ 获取失败。${NC}"
        fi
        url=""
        echo -e "\n按回车键返回..."
        read

    elif [[ $choice == "3" ]]; then
        echo -e "\n${YELLOW}--- 模式 3: AI 语音转字幕 (Whisper) ---${NC}"
        echo "请输入视频文件路径 (默认: $OUTPUT_ROOT):"
        read -e video_path
        video_path=${video_path//\'/}
        video_path=${video_path//\"/}
        video_path=${video_path:-$OUTPUT_ROOT}

        if [[ -z "$video_path" ]]; then
             echo -e "${YELLOW}❌ 路径不能为空${NC}"
        else
             echo -e "\n${GREEN}🚀 开始 AI 转录...${NC}"
             echo "提示: 第一次运行会下载 AI 模型（约 140MB），请保持网络畅通。"
             python3 "$TRANSCRIBE_SCRIPT" "$video_path"
        fi
        echo "按回车键继续..."
        read

    elif [[ $choice == "4" ]]; then
        echo -e "\n${YELLOW}--- 模式 4: 本地视频批量加字幕 ---${NC}"
        echo "该模式将自动处理 $OUTPUT_ROOT 文件夹下的所有视频。"
        
        echo -e "\n${CYAN}请选择具体的加字幕功能:${NC}"
        echo "1. 📖 英加中 (Bilingual: 英文在上, 中文在下)"
        echo "2. 📖 中加英 (Bilingual: 中文在上, 英文在下)"
        echo "3. 🇨🇳 纯中文 (Single: 仅显示中文)"
        echo "4. 🇺🇸 纯英文 (Single: 仅显示英文)"
        read -p "请输入选项 (1-4, 默认 1): " m_choice
        
        mode="bilingual"
        target="zh-CN"
        reverse_flag=""
        
        case $m_choice in
            1) # 英加中: 英文(原)在上, 中文(译)在下
               mode="bilingual"
               target="zh-CN"
               reverse_flag="--reverse" 
               ;;
            2) # 中加英: 中文(原)在上, 英文(译)在下
               mode="bilingual"
               target="en"
               reverse_flag="--reverse"
               ;;
            3) # 纯中文
               mode="zh"
               target="zh-CN"
               ;;
            4) # 纯英文
               mode="en"
               ;;
            *) # 默认英加中
               mode="bilingual"
               target="zh-CN"
               reverse_flag="--reverse"
               ;;
        esac
        
        echo -e "\n${GREEN}🚀 开始执行处理 (功能: $m_choice)...${NC}"
        python3 "$LOCAL_BATCH_SCRIPT" "$OUTPUT_ROOT" --mode "$mode" --target "$target" $reverse_flag
        
        echo "按回车键继续..."
        read

    elif [[ $choice == "5" ]]; then
        echo -e "\n${YELLOW}--- 模式 5: 准备阶段 (剪辑 + 提取) ---${NC}"
        # ... (rest of Mode 5 logic)
        echo "请输入视频文件路径 (默认: $OUTPUT_ROOT):"
        read -e video_path
        video_path=${video_path//\'/}
        video_path=${video_path//\"/}
        video_path=${video_path:-$OUTPUT_ROOT}
        
        echo "请输入字幕文件路径 (默认: 同上):"
        read -e subtitle_path
        subtitle_path=${subtitle_path//\'/}
        subtitle_path=${subtitle_path//\"/}
        subtitle_path=${subtitle_path:-$video_path}
        
        echo "请输入 chapters.json 路径 (默认: 同上):"
        read -e chapters_json
        chapters_json=${chapters_json//\'/}
        chapters_json=${chapters_json//\"/}
        chapters_json=${chapters_json:-$video_path}

        if [[ -z "$video_path" || -z "$subtitle_path" || -z "$chapters_json" ]]; then
             echo -e "${YELLOW}❌ 路径不能为空${NC}"
        else
             echo -e "\n${GREEN}🚀 开始执行...${NC}"
             python3 "$BATCH_SCRIPT" "$video_path" "$subtitle_path" "$chapters_json"
        fi
        echo "按回车键继续..."
        read

    elif [[ $choice == "6" ]]; then
        echo -e "\n${YELLOW}--- 模式 6: 终结阶段 (烧录) ---${NC}"
        # ... (rest of Mode 6 logic)
        echo "请输入视频文件路径 (默认: $OUTPUT_ROOT):"
        read -e video_path
        video_path=${video_path//\'/}
        video_path=${video_path//\"/}
        video_path=${video_path:-$OUTPUT_ROOT}
        
        echo "请输入字幕文件路径 (默认: 同上):"
        read -e subtitle_path
        subtitle_path=${subtitle_path//\'/}
        subtitle_path=${subtitle_path//\"/}
        subtitle_path=${subtitle_path:-$video_path}
        
        echo "请输入 chapters.json 路径 (默认: 同上):"
        read -e chapters_json
        chapters_json=${chapters_json//\'/}
        chapters_json=${chapters_json//\"/}
        chapters_json=${chapters_json:-$video_path}

        if [[ -z "$video_path" || -z "$subtitle_path" || -z "$chapters_json" ]]; then
             echo -e "${YELLOW}❌ 路径不能为空${NC}"
        else
             echo -e "\n${GREEN}🚀 开始执行 (Finalize)...${NC}"
             python3 "$BATCH_SCRIPT" "$video_path" "$subtitle_path" "$chapters_json" --finalize
        fi
        echo "按回车键继续..."
        read

    elif [[ $choice == "7" ]]; then
        echo -e "\n${YELLOW}--- 模式 7: ✨ 动态高亮模式 (Karaoke) ---${NC}"
        echo "该模式将生成逐字变色的高亮字幕，适合知识分享或歌词类视频。"
        echo "请输入视频文件路径 (默认: $OUTPUT_ROOT):"
        read -e video_path
        # 处理可能的空格或引号
        video_path=${video_path//\'/}
        video_path=${video_path//\"/}
        video_path=${video_path:-$OUTPUT_ROOT}

        if [[ -d "$video_path" ]]; then
            # 如果是目录，列出文件让用户选
            echo -e "\n${CYAN}发现以下视频:${NC}"
            ls "$video_path"/*.mp4 2>/dev/null
            read -p "请输入具体视频文件名 (或回车处理目录下第一个 MP4): " v_file
            if [[ -n "$v_file" ]]; then
                video_full_path="$video_path/$v_file"
            else
                video_full_path=$(ls "$video_path"/*.mp4 2>/dev/null | head -n 1)
            fi
        else
            video_full_path="$video_path"
        fi

        if [[ -z "$video_full_path" || ! -f "$video_full_path" ]]; then
            echo -e "${RED}❌ 未找到有效的视频文件: $video_full_path${NC}"
        else
            echo -e "\n${GREEN}🚀 启动动态高亮流程...${NC}"
            python3 "$KARAOKE_SCRIPT" "$video_full_path"
        fi
        echo -e "\n按回车键继续..."
        read

    elif [[ $choice == "8" ]]; then
        echo -e "\n${YELLOW}--- 模式 8: 🎬 蹦蹦蹦模式 (Jump-out) ---${NC}"
        echo "该模式字随声出，背景更干净，视觉冲击力强。"
        echo "请输入视频文件路径 (默认: $OUTPUT_ROOT):"
        read -e video_path
        video_path=${video_path//\'/}
        video_path=${video_path//\"/}
        video_path=${video_path:-$OUTPUT_ROOT}

        if [[ -d "$video_path" ]]; then
            echo -e "\n${CYAN}发现以下视频:${NC}"
            ls "$video_path"/*.mp4 2>/dev/null
            read -p "请输入具体视频文件名 (或回车处理目录下第一个 MP4): " v_file
            if [[ -n "$v_file" ]]; then
                video_full_path="$video_path/$v_file"
            else
                video_full_path=$(ls "$video_path"/*.mp4 2>/dev/null | head -n 1)
            fi
        else
            video_full_path="$video_path"
        fi

        if [[ -z "$video_full_path" || ! -f "$video_full_path" ]]; then
             echo -e "${RED}❌ 未找到有效的视频文件。${NC}"
        else
            echo -e "\n${GREEN}🚀 启动蹦蹦蹦流程...${NC}"
            python3 "$KARAOKE_SCRIPT" "$video_full_path" "popout"
        fi
        echo -e "\n按回车键继续..."
        read

    else
        echo "再见!"
        exit 0
    fi
done
