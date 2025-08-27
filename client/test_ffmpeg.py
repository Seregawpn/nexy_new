#!/usr/bin/env python3
import subprocess

try:
    result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
    print(f"Return code: {result.returncode}")
    print(f"STDOUT: {repr(result.stdout)}")
    print(f"STDERR: {repr(result.stderr)}")
    print(f"STDOUT contains version: {'ffmpeg version' in result.stdout}")
    print(f"STDERR contains version: {'ffmpeg version' in result.stderr}")
    if result.stdout:
        first_line = result.stdout.split('\n')[0]
        print(f"STDOUT first line: {repr(first_line)}")
    if result.stderr:
        first_line = result.stderr.split('\n')[0]
        print(f"STDERR first line: {repr(first_line)}")
except Exception as e:
    print(f"Error: {e}")
