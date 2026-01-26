#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}   YouTube Clipper macOS 一键安装    ${NC}"
echo -e "${GREEN}=====================================${NC}"

# 1. 检查 Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${RED}❌ 未检测到 Homebrew。${NC}"
    echo "请先安装 Homebrew: https://brew.sh/"
    exit 1
fi
echo -e "${GREEN}✅ Homebrew 已安装${NC}"

# 2. 安装/检查 FFmpeg (带 libass)
echo -e "\n${YELLOW}🔍 检查 FFmpeg 环境...${NC}"
if brew list ffmpeg-full &> /dev/null; then
    echo -e "${GREEN}✅ ffmpeg-full 已安装${NC}"
else
    if brew list ffmpeg &> /dev/null; then
        echo -e "${YELLOW}⚠️  发现标准 ffmpeg，可能不支持字幕烧录。${NC}"
        read -p "是否卸载标准 ffmpeg 并安装 ffmpeg-full? (y/n): " install_full
        if [[ $install_full == "y" ]]; then
            brew uninstall ffmpeg
            brew install ffmpeg-full
        else
            echo "跳过安装，可能会导致烧录失败。"
        fi
    else
        echo -e "${YELLOW}⚙️  正在安装 ffmpeg-full...${NC}"
        brew install ffmpeg-full
    fi
fi

# 3. 安装/检查 yt-dlp
echo -e "\n${YELLOW}🔍 检查 yt-dlp...${NC}"
if ! command -v yt-dlp &> /dev/null; then
    echo "正在安装 yt-dlp..."
    brew install yt-dlp
else
    echo -e "${GREEN}✅ yt-dlp 已安装${NC}"
fi

# 4. 安装 Python 依赖
echo -e "\n${YELLOW}🔍 安装 Python 依赖...${NC}"
pip3 install -r requirements.txt

# 5. 配置 .env
echo -e "\n${YELLOW}⚙️  配置环境变量 (.env)...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✅ 已创建 .env 文件${NC}"
    echo -e "${YELLOW}提示: 请稍后编辑 .env 文件配置代理或 API${NC}"
else
    echo -e "${GREEN}✅ .env 文件已存在${NC}"
fi

echo -e "\n${GREEN}=====================================${NC}"
echo -e "${GREEN}   🎉 安装完成！  ${NC}"
echo -e "${GREEN}=====================================${NC}"
echo -e "使用方法:"
echo -e "1. 确保 .env 中配置了网络代理 (如果需要下载 YouTube)"
echo -e "2. 运行 ./run_autoclip.sh 启动一键处理"
