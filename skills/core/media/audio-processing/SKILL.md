---
name: audio-processing
description: Audio processing and editing
version: 1.0.0
category: media
technologies: [ffmpeg, sox, python, pydub]
triggers:
  - audio processing
  - audio editing
  - sound editing
  - audio conversion
---

# Audio Processing

Audio processing, editing, and conversion.

## Tools

- **FFmpeg**: Universal audio/video processing
- **SoX**: Sound eXchange
- **pydub**: Python audio manipulation
- **librosa**: Audio analysis

## FFmpeg Commands

```bash
# Convert format
ffmpeg -i input.wav output.mp3

# Change bitrate
ffmpeg -i input.mp3 -b:a 192k output.mp3

# Extract audio from video
ffmpeg -i video.mp4 -vn -acodec copy output.aac

# Merge audio files
ffmpeg -i "concat:audio1.mp3|audio2.mp3" -acodec copy output.mp3

# Trim audio (start at 10s, duration 30s)
ffmpeg -i input.mp3 -ss 00:00:10 -t 00:00:30 -c copy output.mp3

# Adjust volume
ffmpeg -i input.mp3 -af "volume=2.0" output.mp3

# Remove silence
ffmpeg -i input.mp3 -af silenceremove=1:0:-50dB output.mp3

# Add fade in/out
ffmpeg -i input.mp3 -af "afade=t=in:ss=0:d=3,afade=t=out:st=27:d=3" output.mp3

# Normalize audio
ffmpeg -i input.mp3 -af loudnorm output.mp3
```

## Python with pydub

```python
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range

# Load audio
audio = AudioSegment.from_file("input.mp3")

# Basic operations
audio = audio + 6  # Increase volume by 6dB
audio = audio.fade_in(2000).fade_out(3000)  # Fade in/out

# Trim
audio = audio[5000:30000]  # 5s to 30s

# Concatenate
combined = audio1 + audio2

# Export
audio.export("output.mp3", format="mp3", bitrate="192k")

# Normalize
normalized = normalize(audio)

# Split by silence
from pydub.silence import split_on_silence
chunks = split_on_silence(audio, min_silence_len=500, silence_thresh=-40)
```

## Audio Analysis with librosa

```python
import librosa
import librosa.display
import matplotlib.pyplot as plt

# Load audio
y, sr = librosa.load("audio.mp3")

# Get duration
duration = librosa.get_duration(y=y, sr=sr)

# Detect tempo
tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

# Spectral analysis
spectrogram = librosa.feature.melspectrogram(y=y, sr=sr)
librosa.display.specshow(librosa.power_to_db(spectrogram, ref=np.max))
plt.savefig("spectrogram.png")
```

## Best Practices

1. Always keep original files
2. Use lossless formats for intermediate processing
3. Normalize audio levels
4. Remove silence before/after
5. Match sample rates when combining
6. Use appropriate bitrates for output
7. Test on different playback devices
