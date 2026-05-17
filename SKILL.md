$ cat /tmp/video-transcript/SKILL.md

---
name: video-transcript
description: >
  Extract transcripts from YouTube videos and generate summaries or structured notes.
  Use this skill whenever the user shares a YouTube link (youtube.com or youtu.be) and wants
  to get the transcript, subtitles, captions, or a summary/notes from the video.
  Also trigger when the user pastes a video URL and asks questions like "what does this video say?",
  "summarize this video", "give me the transcript", "帮我提取字幕", "视频总结", "帮我总结这个视频",
  "这个视频讲了什么", or any similar request involving a YouTube video URL.
  Don't wait for the user to say the word "transcript" — if there's a YouTube URL and they want
  to know the content, use this skill.
---

# Video Transcript Skill

Extract the transcript from any YouTube video using a three-tier approach, then return it raw or as a summary.

## Dependencies (one-time setup)

```bash
pip install youtube-transcript-api
pip install openai-whisper
brew install yt-dlp ffmpeg   # or: pip install yt-dlp
```

## Step 1: Run the extraction script

```bash
python3.11 <skill_dir>/scripts/yt_transcript.py "<youtube_url>" 2>/dev/null
```

The script auto-tries three methods in order and returns JSON:
- `success`: true/false
- `transcript`: full text
- `language`: detected language code
- `method`: which tier succeeded ("Tier 1 (API)" / "Tier 2 (yt-dlp subs)" / "Tier 3 (Whisper AI)")

**Tier 1 — youtube-transcript-api** (seconds): fetches official or auto-generated captions via API.

**Tier 2 — yt-dlp subtitle download** (seconds): downloads the auto-generated subtitle file directly. Catches cases where Tier 1 fails due to API restrictions.

**Tier 3 — Whisper AI transcription** (minutes): downloads the audio with yt-dlp, then runs OpenAI Whisper locally to transcribe speech. Works on **any video with audio**, even with zero captions. Uses the `base` model by default.

If all three fail, tell the user in Chinese the video is inaccessible (private, region-blocked, or truly no audio).

> **Note on Tier 3 speed:** Whisper `base` model takes ~1–3 min for a 15-min video. Tell the user it's processing if it takes a while.

## Step 2: Ask what the user wants (if not already specified)

If the user hasn't indicated their preference:

> 字幕已提取成功（通过 [method]）！你想要：
> 1. **完整字幕** — 原始文字，按段落整理
> 2. **AI 摘要** — 提炼核心内容，结构化输出
> 3. **两者都要**

If they said "总结" / "summarize" → go straight to summary.
If they said "字幕" / "原文" → go straight to raw.

## Step 3: Produce the output

### Raw Transcript

```markdown
# 视频字幕 — [Video title or URL]

**语言：** [language]  
**来源：** [url]  
**提取方式：** [method]

---

[Transcript broken into readable paragraphs, ~5–8 sentences each]
```

### Summary (Chinese by default)

```markdown
# 视频摘要 — [Video title or URL]

**来源：** [url]  
**字幕语言：** [language]  
**提取方式：** [method]

---

## 核心主题
[1–2 sentences on what the video is about]

## 主要内容
- [key point 1]
- [key point 2]
- [key point 3]

## 关键结论 / 行动建议
[What does the viewer walk away with?]

---
*摘要由 AI 根据视频字幕生成*
```

Adapt section headers to content type: tutorial → 操作步骤, interview → 嘉宾观点, news → 事件背景, lecture → 核心论点.
