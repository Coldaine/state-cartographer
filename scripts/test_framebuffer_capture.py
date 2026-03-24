#!/usr/bin/env python3
"""
Test script for MEmu framebuffer capture approach.
This script tests the direct fb0 access method described in the task.
"""

import subprocess
import numpy as np
import os
import tempfile
from PIL import Image

def run_adb_command(command):
    """Run an ADB command and return the output."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def get_framebuffer_info():
    """Get framebuffer information from MEmu."""
    print("Getting framebuffer information...")
    
    # Get virtual size
    cmd = 'adb -s 127.0.0.1:21513 shell "su -c \\"cat /sys/class/graphics/fb0/virtual_size\\""'
    returncode, stdout, stderr = run_adb_command(cmd)
    if returncode == 0:
        virtual_size = stdout.strip()
        print(f"Virtual size: {virtual_size}")
    else:
        print(f"Failed to get virtual size: {stderr}")
        virtual_size = "1920x1080"  # fallback
    
    # Get bits per pixel
    cmd = 'adb -s 127.0.0.1:21513 shell "su -c \\"cat /sys/class/graphics/fb0/bits_per_pixel\\""'
    returncode, stdout, stderr = run_adb_command(cmd)
    if returncode == 0:
        bits_per_pixel = stdout.strip()
        print(f"Bits per pixel: {bits_per_pixel}")
    else:
        print(f"Failed to get bits per pixel: {stderr}")
        bits_per_pixel = "32"  # fallback
    
    return virtual_size, bits_per_pixel

def capture_framebuffer_direct():
    """Capture framebuffer directly using cat /dev/graphics/fb0."""
    print("Attempting direct framebuffer capture...")
    
    # Create temp file on device
    cmd = 'adb -s 127.0.0.1:21513 shell "su -c \\"dd if=/dev/graphics/fb0 of=/sdcard/frame.raw bs=8294400 count=1\\""'
    returncode, stdout, stderr = run_adb_command(cmd)
    
    if returncode != 0:
        print(f"Failed to capture framebuffer: {stderr}")
        return None
    
    print("Framebuffer captured to device, pulling to host...")
    
    # Pull the file
    cmd = 'adb -s 127.0.0.1:21513 pull /sdcard/frame.raw'
    returncode, stdout, stderr = run_adb_command(cmd)
    
    if returncode != 0:
        print(f"Failed to pull framebuffer: {stderr}")
        return None
    
    # Read the raw data
    try:
        with open('frame.raw', 'rb') as f:
            raw_data = f.read()
        
        print(f"Captured {len(raw_data)} bytes of framebuffer data")
        
        # Get framebuffer info to parse correctly
        virtual_size, bits_per_pixel = get_framebuffer_info()
        
        # Parse dimensions
        if 'x' in virtual_size:
            width, height = map(int, virtual_size.split('x'))
        else:
            width, height = 1920, 1080  # fallback
        
        # Calculate expected size
        bytes_per_pixel = int(bits_per_pixel) // 8
        expected_size = width * height * bytes_per_pixel
        
        print(f"Expected size: {expected_size} bytes ({width}x{height}x{bytes_per_pixel})")
        print(f"Actual size: {len(raw_data)} bytes")
        
        if len(raw_data) != expected_size:
            print("Warning: Size mismatch, attempting to interpret anyway...")
            # Try to reshape with what we have
            try:
                # Assume RGBA/BGRA format
                frame = np.frombuffer(raw_data, dtype=np.uint8)
                # Try to reshape to closest possible dimensions
                total_pixels = len(frame) // 4
                height = int(np.sqrt(total_pixels * (width/height))) if width > height else int(np.sqrt(total_pixels))
                width = total_pixels // height
                frame = frame.reshape((height, width, 4))
                print(f"Reshaped to: {frame.shape}")
            except Exception as e:
                print(f"Could not reshape frame data: {e}")
                return None
        else:
            # Reshape normally
            frame = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 4))
        
        return frame
        
    except Exception as e:
        print(f"Error processing framebuffer data: {e}")
        return None
    finally:
        # Clean up
        if os.path.exists('frame.raw'):
            os.remove('frame.raw')

def save_frame_as_png(frame, filename="test_framebuffer_capture.png"):
    """Save numpy frame as PNG image."""
    if frame is None:
        print("No frame data to save")
        return False
    
    try:
        # Convert BGRA to RGBA if needed (assuming BGRA format from fb0)
        if frame.shape[2] == 4:
            # Swap B and R channels (BGRA -> RGBA)
            frame_rgba = frame[:, :, [2, 1, 0, 3]]
        else:
            frame_rgba = frame
        
        # Create PIL image and save
        img = Image.fromarray(frame_rgba, 'RGBA')
        img.save(filename)
        print(f"Frame saved as {filename}")
        return True
    except Exception as e:
        print(f"Error saving frame as PNG: {e}")
        return False

def main():
    """Main test function."""
    print("=== MEmu Framebuffer Capture Test ===")
    
    # Test ADB connection first
    print("Testing ADB connection...")
    returncode, stdout, stderr = run_adb_command('adb -s 127.0.0.1:21513 devices')
    if returncode != 0:
        print(f"ADB connection failed: {stderr}")
        return
    
    print(f"ADB devices: {stdout}")
    
    # Test root access
    print("Testing root access...")
    returncode, stdout, stderr = run_adb_command('adb -s 127.0.0.1:21513 shell "su -c \\"echo root_test\\""')
    if returncode != 0:
        print(f"Root access failed: {stderr}")
        print("Note: This test requires root access on MEmu 9")
        return
    
    print(f"Root access test: {stdout.strip()}")
    
    # Attempt framebuffer capture
    frame = capture_framebuffer_direct()
    
    if frame is not None:
        print(f"Successfully captured framebuffer! Shape: {frame.shape}")
        print(f"Data type: {frame.dtype}")
        print(f"Value range: {frame.min()} to {frame.max()}")
        
        # Check if frame is likely black (all zeros or near zeros)
        if np.mean(frame) < 10:
            print("WARNING: Frame appears to be mostly black - this might indicate the issue described")
        else:
            print("SUCCESS: Frame contains non-black data!")
        
        # Save as PNG for verification
        save_frame_as_png(frame, "data/test_framebuffer_capture.png")
    else:
        print("Failed to capture framebuffer")

if __name__ == "__main__":
    main()