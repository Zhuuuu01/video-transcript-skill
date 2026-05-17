# video-transcript-skill

YouTube 视频字幕提取 + 摘要生成 Skill，适用于 Claude Code。

## 功能

丢给 Claude 一个 YouTube 链接，自动提取字幕并生成中文摘要。

三层提取保底：
- **Tier 1** youtube-transcript-api（秒级，有官方字幕时用）
- **Tier 2** yt-dlp 字幕下载（秒级，自动字幕）
- **Tier 3** Whisper AI 语音转录（分钟级，任何有声视频）

## 安装

```bash
# 1. 安装依赖
pip install youtube-transcript-api openai-whisper
brew install yt-dlp ffmpeg

# 2. 安装 Skill（在 Claude Code 里运行）
/install-skill https://github.com/Zhuuuu01/video-transcript-skill/raw/main/video-transcript.skill
