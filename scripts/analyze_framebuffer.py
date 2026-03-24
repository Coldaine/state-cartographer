#!/usr/bin/env python3
"""
Analyze existing framebuffer capture files to determine if they contain non-black frames.
"""

import numpy as np
import os
from PIL import Image

def analyze_raw_file(filepath, width=None, height=None, bytes_per_pixel=4):
    """Analyze a raw framebuffer file."""
    print(f"\n=== Analyzing {filepath} ===")
    
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return None
    
    # Get file size
    size = os.path.getsize(filepath)
    print(f"File size: {size} bytes")
    
    # Read raw data
    with open(filepath, 'rb') as f:
        raw_data = f.read()
    
    print(f"Read {len(raw_data)} bytes")
    
    # Determine dimensions if not provided
    if width is None or height is None:
        # Assume square-ish dimensions based on common aspect ratios
        total_pixels = len(raw_data) // bytes_per_pixel
        # Try common resolutions
        common_resolutions = [
            (1920, 1080),  # Full HD
            (1280, 720),   # HD
            (1024, 1024),  # Square
            (1280, 1024),  # 5:4
        ]
        
        best_match = None
        min_error = float('inf')
        
        for w, h in common_resolutions:
            expected_size = w * h * bytes_per_pixel
            error = abs(expected_size - len(raw_data))
            if error < min_error:
                min_error = error
                best_match = (w, h)
        
        if best_match:
            width, height = best_match
            print(f"Estimated dimensions: {width}x{height} (based on {bytes_per_pixel*8}bpp)")
        else:
            # Fallback: calculate approximate square dimensions
            side = int(np.sqrt(total_pixels))
            width = height = side
            print(f"Using approximate square dimensions: {width}x{height}")
    
    # Calculate expected size
    expected_size = width * height * bytes_per_pixel
    print(f"Expected size for {width}x{height}x{bytes_per_pixel}: {expected_size} bytes")
    
    if len(raw_data) != expected_size:
        print(f"Size mismatch: got {len(raw_data)}, expected {expected_size}")
        # Truncate or pad to fit
        if len(raw_data) > expected_size:
            raw_data = raw_data[:expected_size]
            print(f"Truncated to {expected_size} bytes")
        else:
            # Pad with zeros
            raw_data = raw_data + b'\x00' * (expected_size - len(raw_data))
            print(f"Padded to {expected_size} bytes")
    
    # Convert to numpy array
    try:
        frame = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, bytes_per_pixel))
        print(f"Frame shape: {frame.shape}")
        print(f"Data type: {frame.dtype}")
        print(f"Value range: {frame.min()} to {frame.max()}")
        print(f"Mean value: {np.mean(frame):.2f}")
        
        # Check if mostly black
        black_threshold = 10
        black_pixels = np.sum(frame < black_threshold)
        total_pixels = frame.size
        black_percentage = (black_pixels / total_pixels) * 100
        print(f"Black pixels (< {black_threshold}): {black_pixels}/{total_pixels} ({black_percentage:.1f}%)")
        
        if black_percentage > 90:
            print("WARNING: Frame appears to be mostly black")
        else:
            print("SUCCESS: Frame contains significant non-black data!")
            
        return frame
        
    except Exception as e:
        print(f"Error reshaping frame data: {e}")
        return None

def save_frame_as_png(frame, filename, swap_b_r=False):
    """Save numpy frame as PNG image."""
    if frame is None:
        print("No frame data to save")
        return False
    
    try:
        # Handle different channel counts
        if frame.shape[2] == 4:
            if swap_b_r:
                # Swap B and R channels (BGRA <-> RGBA)
                frame_to_save = frame[:, :, [2, 1, 0, 3]]
            else:
                frame_to_save = frame
            mode = 'RGBA'
        elif frame.shape[2] == 3:
            # Assume RGB
            frame_to_save = frame
            mode = 'RGB'
        else:
            print(f"Unsupported channel count: {frame.shape[2]}")
            return False
        
        # Create PIL image and save
        img = Image.fromarray(frame_to_save, mode)
        img.save(filename)
        print(f"Frame saved as {filename}")
        return True
    except Exception as e:
        print(f"Error saving frame as PNG: {e}")
        return False

def main():
    """Main analysis function."""
    print("=== Framebuffer Analysis ===")
    
    # Files to analyze
    files_to_check = [
        ('data/fb0_21513.raw', None, None, 4),  # Auto-detect dimensions
        ('data/fb0_21513_dd.raw', None, None, 4),
    ]
    
    for filepath, width, height, bpp in files_to_check:
        frame = analyze_raw_file(filepath, width, height, bpp)
        
        if frame is not None:
            # Save analysis results
            base_name = os.path.splitext(os.path.basename(filepath))[0]
            
            # Save as-is
            save_frame_as_png(frame, f"data/{base_name}_analyzed.png", swap_b_r=False)
            
            # Save with B/R swapped (in case it's BGRA)
            save_frame_as_png(frame, f"data/{base_name}_analyzed_rgba.png", swap_b_r=True)
            
            # Print some sample pixel values for visual inspection
            print(f"\nSample pixel values (top-left 5x5):")
            for i in range(min(5, frame.shape[0])):
                row_vals = []
                for j in range(min(5, frame.shape[1])):
                    pixel = frame[i, j]
                    row_vals.append(f"[{pixel[0]},{pixel[1]},{pixel[2]},{pixel[3]}]" if frame.shape[2]==4 else f"[{pixel[0]},{pixel[1]},{pixel[2]}]")
                print("  " + " ".join(row_vals))

if __name__ == "__main__":
    main()