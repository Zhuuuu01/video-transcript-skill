$ cat /tmp/video-transcript/scripts/yt_transcript.py

#!/usr/bin/env python3.11
"""
YouTube 三层字幕提取器
Tier 1: youtube-transcript-api (官方字幕，秒级)
Tier 2: yt-dlp 下载字幕文件 (自动字幕，秒级)
Tier 3: yt-dlp 下载音频 + Whisper AI 转录 (任何有声视频，分钟级)
"""
import re
import sys
import json
import os
import tempfile
import subprocess

def extract_video_id(url: str) -> str | None:
    patterns = [
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/watch\?(?:.*&)?v=([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    if re.fullmatch(r'[a-zA-Z0-9_-]{11}', url.strip()):
        return url.strip()
    return None


def tier1_api(video_id: str) -> dict | None:
    """Tier 1: youtube-transcript-api"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        t = api.fetch(video_id)
        text = re.sub(r'\[.*?\]', '', ' '.join(s.text for s in t.snippets))
        text = re.sub(r'\s+', ' ', text).strip()
        lang = getattr(t, 'language_code', 'unknown')
        return {"transcript": text, "language": lang, "method": "Tier 1 (API)"}
    except Exception:
        return None


def tier2_ytdlp_subs(video_id: str) -> dict | None:
    """Tier 2: yt-dlp 下载字幕文件"""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            url = f"https://www.youtube.com/watch?v={video_id}"
            cmd = [
                "yt-dlp",
                "--write-auto-subs", "--write-subs",
                "--sub-langs", "zh-Hans,zh,en",
                "--skip-download",
                "--output", os.path.join(tmpdir, "sub"),
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            # Find downloaded subtitle file
            vtt_files = [f for f in os.listdir(tmpdir) if f.endswith('.vtt')]
            srt_files = [f for f in os.listdir(tmpdir) if f.endswith('.srt')]
            sub_files = vtt_files + srt_files

            if not sub_files:
                return None

            sub_path = os.path.join(tmpdir, sub_files[0])
            lang = sub_files[0].split('.')[-2] if len(sub_files[0].split('.')) > 2 else 'unknown'

            with open(sub_path, 'r', encoding='utf-8') as f:
                raw = f.read()

            # Parse VTT/SRT: remove timestamps, deduplicate lines
            lines = raw.split('\n')
            seen = set()
            text_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if re.match(r'^\d{2}:\d{2}', line):
                    continue
                if line in ('WEBVTT', 'NOTE') or line.startswith('Kind:') or line.startswith('Language:'):
                    continue
                if re.match(r'^\d+$', line):
                    continue
                # Remove VTT tags
                clean = re.sub(r'<[^>]+>', '', line).strip()
                clean = re.sub(r'\[.*?\]', '', clean).strip()
                if clean and clean not in seen:
                    seen.add(clean)
                    text_lines.append(clean)

            transcript = ' '.join(text_lines)
            transcript = re.sub(r'\s+', ' ', transcript).strip()
            if len(transcript) < 50:
                return None
            return {"transcript": transcript, "language": lang, "method": "Tier 2 (yt-dlp subs)"}
    except Exception:
        return None


def tier3_whisper(video_id: str) -> dict | None:
    """Tier 3: yt-dlp 下载音频 + Whisper 转录"""
    try:
        import whisper
    except ImportError:
        print("  [Tier 3] Whisper 未安装，跳过", file=sys.stderr)
        return None

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            url = f"https://www.youtube.com/watch?v={video_id}"
            audio_path = os.path.join(tmpdir, "audio.mp3")

            print("  [Tier 3] 下载音频中...", file=sys.stderr)
            cmd = [
                "yt-dlp",
                "--extract-audio", "--audio-format", "mp3",
                "--audio-quality", "5",
                "--output", audio_path,
                url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if not os.path.exists(audio_path):
                # yt-dlp may append extension
                mp3s = [f for f in os.listdir(tmpdir) if f.endswith('.mp3')]
                if not mp3s:
                    return None
                audio_path = os.path.join(tmpdir, mp3s[0])

            print("  [Tier 3] Whisper 转录中 (base 模型)...", file=sys.stderr)
            model = whisper.load_model("base")
            result = model.transcribe(audio_path)
            transcript = result["text"].strip()
            lang = result.get("language", "unknown")

            return {"transcript": transcript, "language": lang, "method": "Tier 3 (Whisper AI)"}
    except Exception as e:
        print(f"  [Tier 3] 失败: {e}", file=sys.stderr)
        return None


def get_transcript(url: str) -> dict:
    video_id = extract_video_id(url)
    if not video_id:
        return {"success": False, "error": f"无法解析视频 ID: {url}"}

    print(f"视频 ID: {video_id}", file=sys.stderr)

    print("[Tier 1] 尝试 API 提取...", file=sys.stderr)
    result = tier1_api(video_id)
    if result:
        return {"success": True, "video_id": video_id, **result}

    print("[Tier 2] 尝试 yt-dlp 字幕下载...", file=sys.stderr)
    result = tier2_ytdlp_subs(video_id)
    if result:
        return {"success": True, "video_id": video_id, **result}

    print("[Tier 3] 尝试 Whisper AI 转录...", file=sys.stderr)
    result = tier3_whisper(video_id)
    if result:
        return {"success": True, "video_id": video_id, **result}

    return {"success": False, "error": "三种方式均失败，该视频可能无法访问或受版权保护"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "用法: python3.11 yt_transcript.py <youtube_url>"}))
        sys.exit(1)

    output = get_transcript(sys.argv[1])
    if output.get("success"):
        # Print just transcript to stdout, rest to stderr
        print(json.dumps(output, ensure_ascii=False))
    else:
        print(json.dumps(output, ensure_ascii=False))
        sys.exit(1)
