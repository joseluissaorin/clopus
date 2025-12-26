---
name: whisper-transcription
description: Transcribe audio and video to text using OpenAI Whisper
version: 1.0.0
author: CLOPUS
tools:
  - Bash
triggers:
  - whisper
  - transcription
  - transcribe
  - audio to text
  - speech to text
---

# Whisper Transcription

## Context

You are an expert in audio transcription using OpenAI's Whisper for:
- Audio/video transcription
- Multi-language support
- Subtitle generation
- Translation
- Speaker diarization (with extensions)

## Installation

```bash
# Using pip
pip install openai-whisper

# For faster inference with GPU
pip install openai-whisper torch torchvision torchaudio

# Using faster-whisper (CTranslate2 optimized)
pip install faster-whisper
```

## Basic Usage

### 1. Command Line Transcription

```bash
# Basic transcription
whisper audio.mp3

# Specify model (tiny, base, small, medium, large)
whisper audio.mp3 --model medium

# Specify language
whisper audio.mp3 --language en

# Output format
whisper audio.mp3 --output_format txt
whisper audio.mp3 --output_format srt
whisper audio.mp3 --output_format vtt
whisper audio.mp3 --output_format json
whisper audio.mp3 --output_format all

# Output directory
whisper audio.mp3 --output_dir ./transcripts
```

### 2. Python API

```python
import whisper

# Load model
model = whisper.load_model("medium")

# Transcribe
result = model.transcribe("audio.mp3")

# Access results
print(result["text"])  # Full text
print(result["segments"])  # Timestamped segments
print(result["language"])  # Detected language

# With options
result = model.transcribe(
    "audio.mp3",
    language="en",  # Force language
    task="transcribe",  # or "translate" for English translation
    fp16=True,  # Use half precision (GPU)
    verbose=True,  # Show progress
)
```

### 3. Faster-Whisper (Optimized)

```python
from faster_whisper import WhisperModel

# Load model (uses CTranslate2)
model = WhisperModel("medium", device="cuda", compute_type="float16")

# Transcribe
segments, info = model.transcribe("audio.mp3", beam_size=5)

print(f"Detected language: {info.language} ({info.language_probability:.2f})")

for segment in segments:
    print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
```

### 4. Subtitle Generation

```python
import whisper

def generate_subtitles(audio_path, output_path, model_name="medium"):
    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path)

    # Generate SRT format
    with open(output_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(result["segments"], 1):
            start = format_timestamp(segment["start"])
            end = format_timestamp(segment["end"])
            text = segment["text"].strip()

            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

# Usage
generate_subtitles("video.mp4", "subtitles.srt")
```

### 5. Translation to English

```python
import whisper

model = whisper.load_model("medium")

# Translate any language to English
result = model.transcribe("spanish_audio.mp3", task="translate")
print(result["text"])  # Translated English text
```

### 6. Batch Processing

```bash
#!/bin/bash
# batch_transcribe.sh

MODEL="medium"
OUTPUT_DIR="./transcripts"
FORMAT="srt"

mkdir -p "$OUTPUT_DIR"

for file in audio/*.mp3; do
    filename=$(basename "$file" .mp3)
    echo "Transcribing: $filename"
    whisper "$file" \
        --model "$MODEL" \
        --output_format "$FORMAT" \
        --output_dir "$OUTPUT_DIR"
done
```

```python
# Python batch processing
import whisper
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

def transcribe_file(model, audio_path, output_dir):
    result = model.transcribe(str(audio_path))

    output_path = output_dir / f"{audio_path.stem}.txt"
    with open(output_path, "w") as f:
        f.write(result["text"])

    return audio_path.name, len(result["text"])

def batch_transcribe(audio_dir, output_dir, model_name="medium"):
    model = whisper.load_model(model_name)
    audio_dir = Path(audio_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    audio_files = list(audio_dir.glob("*.mp3")) + list(audio_dir.glob("*.wav"))

    for audio_file in audio_files:
        name, length = transcribe_file(model, audio_file, output_dir)
        print(f"Transcribed {name}: {length} characters")
```

### 7. Extract Audio from Video

```bash
# Extract audio for transcription
ffmpeg -i video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav

# Then transcribe
whisper audio.wav --model medium
```

### 8. Word-Level Timestamps

```python
import whisper

model = whisper.load_model("medium")

# Enable word timestamps
result = model.transcribe(
    "audio.mp3",
    word_timestamps=True
)

for segment in result["segments"]:
    for word in segment.get("words", []):
        print(f"{word['word']}: {word['start']:.2f}s - {word['end']:.2f}s")
```

## Model Sizes

| Model  | Parameters | English-only | Multilingual | VRAM  |
|--------|-----------|--------------|--------------|-------|
| tiny   | 39M       | ~1 GB        | ~1 GB        | ~1 GB |
| base   | 74M       | ~1 GB        | ~1 GB        | ~1 GB |
| small  | 244M      | ~2 GB        | ~2 GB        | ~2 GB |
| medium | 769M      | ~5 GB        | ~5 GB        | ~5 GB |
| large  | 1550M     | N/A          | ~10 GB       | ~10 GB |

## Best Practices

1. **Use appropriate model size** - Larger = more accurate but slower
2. **Preprocess audio** - 16kHz mono WAV is optimal
3. **Specify language when known** - Faster and more accurate
4. **Use GPU when available** - Much faster processing
5. **Consider faster-whisper** - 4x faster with same accuracy

## Output Formats

- **txt** - Plain text
- **srt** - SubRip subtitles
- **vtt** - WebVTT subtitles
- **json** - Full data with timestamps
- **tsv** - Tab-separated values
