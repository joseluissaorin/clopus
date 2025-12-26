---
name: imagemagick-images
description: Process, convert, and manipulate images using ImageMagick
version: 1.0.0
author: CLOPUS
tools:
  - Bash
triggers:
  - imagemagick
  - image processing
  - image conversion
  - resize image
  - convert image
---

# ImageMagick Image Processing

## Context

You are an expert in image processing using ImageMagick for:
- Format conversion
- Resizing and cropping
- Image optimization
- Watermarks and annotations
- Batch processing
- Image composition

## Common Operations

### 1. Format Conversion

```bash
# Basic conversion
convert input.png output.jpg

# With quality setting
convert input.png -quality 85 output.jpg

# Convert to WebP
convert input.jpg -quality 80 output.webp

# Convert to PDF
convert image1.jpg image2.jpg output.pdf

# Convert PDF to images
convert -density 300 input.pdf output-%03d.png
```

### 2. Resizing

```bash
# Resize to specific dimensions
convert input.jpg -resize 800x600 output.jpg

# Resize maintaining aspect ratio (fit within)
convert input.jpg -resize 800x600\> output.jpg

# Resize to exact dimensions (may distort)
convert input.jpg -resize 800x600! output.jpg

# Resize by percentage
convert input.jpg -resize 50% output.jpg

# Resize width, auto height
convert input.jpg -resize 800x output.jpg

# Thumbnail with fixed dimensions
convert input.jpg -thumbnail 200x200^ -gravity center -extent 200x200 output.jpg
```

### 3. Cropping

```bash
# Crop to size from position
convert input.jpg -crop 400x300+100+50 output.jpg

# Crop center
convert input.jpg -gravity center -crop 400x300+0+0 +repage output.jpg

# Auto-crop whitespace
convert input.jpg -trim +repage output.jpg

# Crop with padding
convert input.jpg -trim -bordercolor white -border 20 output.jpg
```

### 4. Optimization

```bash
# Strip metadata
convert input.jpg -strip output.jpg

# Optimize JPEG
convert input.jpg -strip -interlace Plane -quality 85 output.jpg

# Optimize PNG
convert input.png -strip -colors 256 output.png

# Create progressive JPEG
convert input.jpg -interlace JPEG -quality 80 output.jpg

# Compress for web
convert input.jpg -resize 1920x1080\> -strip -quality 80 output.jpg
```

### 5. Watermarks

```bash
# Add text watermark
convert input.jpg -gravity southeast -fill white -pointsize 20 \
  -annotate +10+10 "© 2024 Company" output.jpg

# Add image watermark
composite -gravity southeast -geometry +10+10 watermark.png input.jpg output.jpg

# Tiled watermark
convert input.jpg -fill "rgba(255,255,255,0.3)" \
  -draw "rotate 45 text 100,100 'WATERMARK'" output.jpg

# Semi-transparent overlay
composite -dissolve 30% watermark.png input.jpg output.jpg
```

### 6. Effects and Filters

```bash
# Blur
convert input.jpg -blur 0x5 output.jpg

# Sharpen
convert input.jpg -sharpen 0x1 output.jpg

# Grayscale
convert input.jpg -colorspace Gray output.jpg

# Sepia
convert input.jpg -sepia-tone 80% output.jpg

# Brightness/contrast
convert input.jpg -brightness-contrast 10x5 output.jpg

# Rotate
convert input.jpg -rotate 90 output.jpg

# Mirror/flip
convert input.jpg -flip output.jpg
convert input.jpg -flop output.jpg

# Border
convert input.jpg -bordercolor black -border 10 output.jpg

# Round corners
convert input.jpg \( +clone -alpha extract \
  -draw 'fill black polygon 0,0 0,15 15,0 fill white circle 15,15 15,0' \
  \( +clone -flip \) -compose Multiply -composite \
  \( +clone -flop \) -compose Multiply -composite \
  \) -alpha off -compose CopyOpacity -composite output.png
```

### 7. Image Composition

```bash
# Side by side
convert +append left.jpg right.jpg combined.jpg

# Stack vertically
convert -append top.jpg bottom.jpg combined.jpg

# Overlay at position
composite -geometry +100+50 overlay.png base.jpg output.jpg

# Grid of images
montage img1.jpg img2.jpg img3.jpg img4.jpg -geometry 200x200+2+2 -tile 2x2 grid.jpg

# Collage with labels
montage *.jpg -label '%f' -geometry 200x200+2+2 collage.jpg
```

### 8. Batch Processing

```bash
# Convert all PNGs to JPGs
mogrify -format jpg *.png

# Resize all images
mogrify -resize 800x600 *.jpg

# Add suffix to batch conversion
for f in *.jpg; do convert "$f" -resize 50% "${f%.jpg}_small.jpg"; done

# Parallel batch processing
find . -name "*.jpg" | parallel convert {} -resize 800x600 resized/{}

# Using mogrify with output directory
mogrify -path output/ -resize 800x600 -format jpg *.png
```

### 9. Sprites and Icons

```bash
# Create sprite sheet
montage icon*.png -tile 10x -geometry +0+0 -background none sprite.png

# Generate favicon sizes
for size in 16 32 48 64 128 256; do
  convert icon.png -resize ${size}x${size} icon-${size}.png
done

# Create ICO file
convert icon-16.png icon-32.png icon-48.png icon-64.png favicon.ico

# Generate app icons
convert icon.png -resize 512x512 icon-512.png
convert icon.png -resize 192x192 icon-192.png
convert icon.png -resize 180x180 apple-touch-icon.png
```

### 10. Information and Analysis

```bash
# Get image info
identify image.jpg

# Detailed info
identify -verbose image.jpg

# Get dimensions only
identify -format "%wx%h" image.jpg

# Get color histogram
convert image.jpg -colors 16 -format "%c" histogram:info:-

# Compare images
compare image1.jpg image2.jpg diff.jpg
```

## Best Practices

1. **Use mogrify for in-place edits** - Faster for batch operations
2. **Preserve originals** - Work on copies
3. **Use appropriate quality** - 80-85 for JPEG is usually good
4. **Strip metadata** - Reduce file size for web
5. **Use \> suffix** - Prevent upscaling

## Useful Options

```bash
-quality N       # Set quality (0-100)
-strip           # Remove metadata
-interlace TYPE  # Progressive loading
-colorspace      # Color space conversion
-density DPI     # Set resolution
-units           # Units for density
+repage          # Reset virtual canvas
-background      # Set background color
-alpha           # Alpha channel operations
```
