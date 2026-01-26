---
name: youtube-clipper
description: >
  YouTube 视频智能剪辑工具。下载视频和字幕，AI 分析生成精细章节（几分钟级别），
  用户选择片段后自动剪辑、翻译字幕为中英双语、烧录字幕到视频，并生成总结文案。
  使用场景：当用户需要剪辑 YouTube 视频、生成短视频片段、制作双语字幕版本时。
  关键词：视频剪辑、YouTube、字幕翻译、双语字幕、视频下载、clip video
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - AskUserQuestion
model: claude-sonnet-4-5-20250514
---

# YouTube 视频智能剪辑工具

> **Installation**: If you're installing this skill from GitHub, please refer to [README.md](README.md#installation) for installation instructions. The recommended method is `npx skills add https://github.com/op7418/Youtube-clipper-skill`.

## 工作流程

你将按照以下 8 个阶段执行 YouTube 视频剪辑任务：

### 阶段 1: 环境检测

**目标**: 确保所有必需工具和依赖都已安装

1. 检测 yt-dlp 是否可用
   ```bash
   yt-dlp --version
   ```

2. 检测 FFmpeg 版本和 libass 支持
   ```bash
   # 优先检查 ffmpeg-full（macOS）
   /opt/homebrew/opt/ffmpeg-full/bin/ffmpeg -version

   # 检查标准 FFmpeg
   ffmpeg -version

   # 验证 libass 支持（字幕烧录必需）
   ffmpeg -filters 2>&1 | grep subtitles
   ```

3. 检测 Python 依赖
   ```bash
   python3 -c "import yt_dlp; print('✅ yt-dlp available')"
   python3 -c "import pysrt; print('✅ pysrt available')"
   python3 -c "import whisper; print('✅ whisper available')"
   ```

**如果环境检测失败**:
- yt-dlp 未安装: 提示 `brew install yt-dlp` 或 `pip install yt-dlp`
- FFmpeg 无 libass: 提示安装 ffmpeg-full
  ```bash
  brew install ffmpeg-full  # macOS
  ```
- Python 依赖缺失: 提示 `pip install pysrt python-dotenv openai-whisper`

**注意**:
- 标准 Homebrew FFmpeg 不包含 libass，无法烧录字幕
- ffmpeg-full 路径: `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg` (Apple Silicon)
- 必须先通过环境检测才能继续

---

### 阶段 2: 下载视频

**目标**: 下载 YouTube 视频和英文字幕

1. 询问用户 YouTube URL

2. 调用 download_video.py 脚本
   ```bash
   cd ~/.claude/skills/youtube-clipper
   python3 scripts/download_video.py <youtube_url>
   ```

3. 脚本会：
   - 下载视频（最高 1080p，mp4 格式）
   - 下载英文字幕（VTT 格式，自动字幕作为备选）
   - **注意**: 目前仅支持下载英文字幕，忽略原视频的其他语言字幕（包括中文）。
   - 输出文件路径和视频信息

4. 向用户展示：
   - 视频标题
   - 视频时长
   - 文件大小
   - 下载路径

**输出**:
- 视频文件: `<id>.mp4`（使用视频 ID 命名，避免特殊字符问题）
- 字幕文件: `<id>.en.vtt`

---

### 阶段 3: 只下字幕 (可选极速模式)

**目标**: 快速拉取英文字幕 VTT 文件，无需下载视频

1. 使用启动器模式 2。
2. 脚本会跳过视频流，仅提取 English 字幕，适用于快速分析内容。

---

### 阶段 4: AI 转录 (针对无字幕视频)

**目标**: 如果视频没有下载到字幕，使用本地 Whisper 模型生成字幕轨道

1. 调用 transcribe_video.py 脚本
   ```bash
   python3 scripts/transcribe_video.py <video_path>
   ```

2. 脚本会：
   - 自动寻找系统 /opt/homebrew/bin/whisper
   - 提取音频并使用 base 模型转录
   - 生成 .en.srt 文件

---

### 阶段 5: 本地一键批量处理 (推荐)

**目标**: 对 download 文件夹内的文件进行“识别+翻译+压制”全自动处理

1. 启动器模式 4：一键循环处理。
2. 此步骤会自动：
   - 为缺失字幕的视频跑 Whisper。
   - 调用免 API 翻译引擎生成中英双语版。
   - 自动检测视频分辨率，对竖屏（抖音比例）执行偏移量上提。
   - 烧录最终视频。

---

### 阶段 6: 分析章节（高级剪辑功能）

**目标**: 使用 Claude AI 分析字幕内容，生成精细章节（2-5 分钟级别）

1. 调用 analyze_subtitles.py 解析 VTT 字幕
   ```bash
   python3 scripts/analyze_subtitles.py <subtitle_path>
   ```

2. 脚本会输出结构化字幕数据：
   - 完整字幕文本（带时间戳）
   - 总时长
   - 字幕条数

3. **你需要执行 AI 分析**（这是最关键的步骤）：
   - 阅读完整字幕内容
   - 理解内容语义和主题转换点
   - 识别自然的话题切换位置
   - 生成 2-5 分钟粒度的章节（避免半小时粗粒度切分）

4. 为每个章节生成：
   - **标题**: 精炼的主题概括（10-20 字）
   - **时间范围**: 起始和结束时间（格式: MM:SS 或 HH:MM:SS）
   - **核心摘要**: 1-2 句话说明这段讲了什么（50-100 字）
   - **关键词**: 3-5 个核心概念词

5. **章节生成原则**：
   - 粒度：每个章节 2-5 分钟（避免太短或太长）
   - 完整性：确保所有视频内容都被覆盖，无遗漏
   - 有意义：每个章节是一个相对独立的话题
   - 自然切分：在主题转换点切分，不要机械地按时间切

6. 向用户展示章节列表：
   ```
   📊 分析完成，生成 X 个章节：

   ... (所有章节)

   ✓ 所有内容已覆盖，无遗漏
   ```

**注意 (手动操作)**: 发挥 AI 最大价值的最佳方式是让 AI 手导分析字幕。如果你在本地运行且不想通过 API 逐条翻译，可以：
1. 发送字幕给 AI 让其分析。
2. 将 AI 提供的符合格式的 JSON 保存为 `download/chapters.json`。
3. 如果所有文件都在 `download` 文件夹，接下来的步骤只需一路回车。

---

### 阶段 7: 切片处理 (语义剪辑)

**目标**: 使用批量处理脚本自动完成剪辑、提取和烧录

1. **准备章节文件**
   将分析生成的章节信息保存为 `chapters.json`。

2. **执行处理**
   使用启动器模式 5 & 6 分别进行剪辑准备和最终烧录。

---

### 阶段 8: 输出结果

**目标**: 展示最终成品

1. 展示生成的文件（通常带 `_burned` 或在 `youtube-clips/` 目录下）。
2. 提供社交媒体总结建议。

---

## 关键技术点

### 1. FFmpeg 路径空格问题
**问题**: FFmpeg subtitles 滤镜无法正确解析包含空格的路径

**解决方案**: burn_subtitles.py 使用临时目录
- 创建无空格临时目录
- 复制文件到临时目录
- 执行 FFmpeg
- 移动输出文件回目标位置

### 2. 批量翻译优化
**问题**: 逐条翻译会产生大量 API 调用

**解决方案**: 每批 20 条字幕一起翻译
- 节省 95% API 调用
- 提高翻译速度
- 保持翻译一致性

### 3. 章节分析精细度
**目标**: 生成 2-5 分钟粒度的章节，避免半小时粗粒度

**方法**:
- 理解字幕语义，识别主题转换
- 寻找自然的话题切换点
- 确保每个章节有完整的论述
- 避免机械按时间切分

### 4. 竖屏 UI 适配
**问题**: 抖音/Shorts 底部有点赞和标题，普通字幕会被挡住。

**方法**:
- 自动检测分辨率：高 > 宽 判定为竖屏。
- 动态 MarginV：竖屏自动设置 `MarginV=110`，将字幕上移至安全区。
- 动态 FontSize：适配窄高屏幕。

### 5. 免 API 翻译架构
**特点**:
- 使用 `deep-translator` 驱动的 Google 接口。
- **无需 Key**：完全免费运行。
- 支持 `bilingual` (双/中英), `zh` (中), `en` (英) 三类渲染模式。

---

## 错误处理

### 环境问题
- 缺少工具 → 提示安装命令
- FFmpeg 无 libass → 引导安装 ffmpeg-full
- Python 依赖缺失 → 提示 pip install

### 下载问题
- 无效 URL → 提示检查 URL 格式
- 字幕缺失 → 尝试自动字幕
- 网络错误 → 提示重试

### 处理问题
- FFmpeg 执行失败 → 显示详细错误信息
- 翻译失败 → 重试机制（最多 3 次）
- 磁盘空间不足 → 提示清理空间

---

## 输出文件命名规范

- 视频片段: `<章节标题>_clip.mp4`
- 字幕文件: `<章节标题>_bilingual.srt`
- 烧录版本: `<章节标题>_with_subtitles.mp4`
- 总结文案: `<章节标题>_summary.md`

**文件名处理**:
- 移除特殊字符（`/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`）
- 空格替换为下划线
- 限制长度（最多 100 字符）

---

## 用户体验要点

1. **进度可见**: 每个步骤都展示进度和状态
2. **错误友好**: 清晰的错误信息和解决方案
3. **可控性**: 用户选择要剪辑的章节和处理选项
4. **高质量**: 章节分析有意义，翻译准确流畅
5. **完整性**: 提供原始和处理后的多个版本

---

## 开始执行

当用户触发这个 Skill 时：
1. 立即开始阶段 1（环境检测）
2. 按照 6 个阶段顺序执行
3. 每个阶段完成后自动进入下一阶段
4. 遇到问题时提供清晰的解决方案
5. 最后展示完整的输出结果

记住：这个 Skill 的核心价值在于 **AI 精细章节分析** 和 **无缝的技术处理**，让用户能快速从长视频中提取高质量的短视频片段。
