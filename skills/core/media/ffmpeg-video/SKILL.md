---
name: ffmpeg-video
description: Process, convert, and manipulate video files using FFmpeg
version: 1.0.0
author: CLOPUS
tools:
  - Bash
triggers:
  - ffmpeg
  - video
  - video editing
  - video conversion
  - transcode
---

# FFmpeg Video Processing

## Context

You are an expert in video processing using FFmpeg for:
- Format conversion
- Video compression
- Trimming and concatenation
- Adding overlays and watermarks
- Audio extraction and manipulation
- Streaming preparation

## Common Operations

### 1. Format Conversion

```bash
# Convert to MP4 (H.264)
ffmpeg -i input.avi -c:v libx264 -c:a aac output.mp4

# Convert to WebM (VP9)
ffmpeg -i input.mp4 -c:v libvpx-vp9 -c:a libopus output.webm

# Convert to GIF
ffmpeg -i input.mp4 -vf "fps=10,scale=320:-1" output.gif

# Convert to audio only
ffmpeg -i input.mp4 -vn -c:a libmp3lame -q:a 2 output.mp3
```

### 2. Compression

```bash
# Compress with CRF (lower = better quality, 18-28 typical)
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset medium output.mp4

# Two-pass encoding for target bitrate
ffmpeg -i input.mp4 -c:v libx264 -b:v 2M -pass 1 -f null /dev/null
ffmpeg -i input.mp4 -c:v libx264 -b:v 2M -pass 2 output.mp4

# Reduce file size aggressively
ffmpeg -i input.mp4 -c:v libx264 -crf 28 -preset slow -c:a aac -b:a 128k output.mp4
```

### 3. Trimming and Cutting

```bash
# Trim from start time to duration
ffmpeg -i input.mp4 -ss 00:01:00 -t 00:00:30 -c copy output.mp4

# Trim from start to end time
ffmpeg -i input.mp4 -ss 00:01:00 -to 00:01:30 -c copy output.mp4

# Fast seek (put -ss before -i for speed)
ffmpeg -ss 00:01:00 -i input.mp4 -t 00:00:30 -c copy output.mp4

# Remove first 10 seconds
ffmpeg -i input.mp4 -ss 10 -c copy output.mp4
```

### 4. Concatenation

```bash
# Create file list
echo "file 'part1.mp4'" > filelist.txt
echo "file 'part2.mp4'" >> filelist.txt
echo "file 'part3.mp4'" >> filelist.txt

# Concatenate with same codec
ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4

# Concatenate with re-encoding
ffmpeg -f concat -safe 0 -i filelist.txt -c:v libx264 -c:a aac output.mp4
```

### 5. Resolution and Scaling

```bash
# Scale to 720p (maintain aspect ratio)
ffmpeg -i input.mp4 -vf "scale=-1:720" output.mp4

# Scale to specific size
ffmpeg -i input.mp4 -vf "scale=1280:720" output.mp4

# Scale with padding (letterbox)
ffmpeg -i input.mp4 -vf "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2" output.mp4

# Crop video
ffmpeg -i input.mp4 -vf "crop=640:480:100:50" output.mp4
```

### 6. Watermarks and Overlays

```bash
# Add image watermark (bottom right)
ffmpeg -i input.mp4 -i watermark.png -filter_complex "overlay=W-w-10:H-h-10" output.mp4

# Add text overlay
ffmpeg -i input.mp4 -vf "drawtext=text='Sample Text':fontsize=24:fontcolor=white:x=10:y=10" output.mp4

# Add timestamp
ffmpeg -i input.mp4 -vf "drawtext=text='%{pts\:hms}':fontsize=20:fontcolor=white:x=10:y=10" output.mp4
```

### 7. Audio Operations

```bash
# Extract audio
ffmpeg -i input.mp4 -vn -c:a copy output.aac

# Replace audio
ffmpeg -i input.mp4 -i new_audio.mp3 -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 output.mp4

# Adjust volume
ffmpeg -i input.mp4 -af "volume=2.0" output.mp4

# Normalize audio
ffmpeg -i input.mp4 -af loudnorm output.mp4

# Remove audio
ffmpeg -i input.mp4 -an -c:v copy output.mp4
```

### 8. Speed Adjustment

```bash
# Speed up 2x (video and audio)
ffmpeg -i input.mp4 -vf "setpts=0.5*PTS" -af "atempo=2.0" output.mp4

# Slow down 0.5x
ffmpeg -i input.mp4 -vf "setpts=2.0*PTS" -af "atempo=0.5" output.mp4

# Create timelapse (30x speed)
ffmpeg -i input.mp4 -vf "setpts=0.033*PTS" -an output.mp4
```

### 9. Frame Extraction

```bash
# Extract single frame at timestamp
ffmpeg -i input.mp4 -ss 00:00:10 -frames:v 1 frame.jpg

# Extract frames as image sequence
ffmpeg -i input.mp4 -vf "fps=1" frames/frame_%04d.jpg

# Extract thumbnail every 10 seconds
ffmpeg -i input.mp4 -vf "fps=1/10" thumbnails/thumb_%03d.jpg
```

### 10. Streaming Preparation (HLS)

```bash
# Create HLS stream
ffmpeg -i input.mp4 -c:v libx264 -c:a aac -hls_time 10 -hls_list_size 0 -f hls output.m3u8

# Multi-bitrate HLS
ffmpeg -i input.mp4 \
  -c:v libx264 -b:v:0 800k -s:v:0 640x360 \
  -c:v libx264 -b:v:1 1400k -s:v:1 842x480 \
  -c:v libx264 -b:v:2 2800k -s:v:2 1280x720 \
  -c:a aac -b:a 128k \
  -var_stream_map "v:0,a:0 v:1,a:1 v:2,a:2" \
  -master_pl_name master.m3u8 \
  -f hls -hls_time 6 -hls_list_size 0 \
  -hls_segment_filename "stream_%v/segment_%03d.ts" \
  stream_%v/playlist.m3u8
```

## Best Practices

1. **Use -c copy when possible** - Faster, no quality loss
2. **Choose appropriate CRF** - Balance quality vs size
3. **Use presets wisely** - slower = better compression
4. **Test with short clips** - Before processing large files
5. **Check codec support** - Not all containers support all codecs

## Useful Flags

```bash
-y              # Overwrite output without asking
-n              # Don't overwrite
-hide_banner    # Less verbose output
-stats          # Show encoding progress
-v quiet        # Suppress output
-threads 0      # Auto-detect threads
```
