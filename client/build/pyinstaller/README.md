# AI Voice Assistant - macOS Build Guide

## Overview
This guide explains how to build and package the AI Voice Assistant for macOS, specifically designed for users with visual impairments.

## Prerequisites

### System Requirements
- macOS 12.0+ (Monterey) or later
- Apple Silicon (M1/M2) Mac
- Python 3.12+
- Homebrew (for additional tools)

### Required Software
- PyInstaller 6.15+
- create-dmg (for DMG creation)
- All Python dependencies (see requirements.txt)

## Build Process

### Quick Start
Run the complete build process with one command:
```bash
./build/pyinstaller/full_build.sh
```

### Step-by-Step Build

#### 1. Test Build Environment
```bash
./build/pyinstaller/test_build.sh
```
This script checks:
- PyInstaller installation
- Required files presence
- Icon availability
- PyInstaller functionality

#### 2. Build Application
```bash
./build/pyinstaller/build_script.sh
```
This creates:
- `Nexy.app` bundle
- Optimized for Apple Silicon
- Background mode enabled
- All dependencies included

#### 3. Create DMG Installer
```bash
./build/pyinstaller/create_dmg.sh
```
This generates:
- Professional DMG installer
- Automatic installation setup
- Optimized for blind users

#### 4. Setup Autostart
```bash
./build/pyinstaller/setup_autostart.sh
```
This provides:
- Step-by-step autostart instructions
- Manual setup guidance
- Alternative launch methods

## Configuration

### Application Settings
Edit `config/app_config.yaml`:
```yaml
grpc:
  server_host: "YOUR_EXTERNAL_SERVER_IP"  # Replace with actual IP
  server_port: 50051
  timeout: 30
  retry_attempts: 3
```

### Build Settings
Edit `build/pyinstaller/app.spec`:
- Application name and version
- Icon path
- Bundle identifier
- Architecture settings

## Features

### Background Mode
- `LSUIElement: True` - Hides from Dock
- Runs silently in background
- Accessible via keyboard shortcuts

### Accessibility
- VoiceOver compatible
- Screen reader support
- Keyboard navigation
- High contrast support

### Permissions
- Microphone access for speech recognition
- Screen recording for context analysis
- Automation permissions for system control

## Distribution

### DMG Installer
- Professional appearance
- Automatic installation
- User-friendly interface
- VoiceOver optimized

### Installation Process
1. Double-click DMG file
2. Drag app to Applications folder
3. Grant required permissions
4. Setup autostart (optional)

## Troubleshooting

### Common Issues

#### Build Failures
- Check Python version compatibility
- Verify all dependencies installed
- Ensure sufficient disk space
- Check file permissions

#### Runtime Issues
- Verify external server connectivity
- Check microphone permissions
- Ensure screen recording access
- Review application logs

#### Permission Issues
- System Preferences → Security & Privacy
- Grant microphone access
- Allow screen recording
- Enable automation

### Logs
Application logs are stored at:
```
~/Library/Logs/Nexy/app.log
```

## Support

### Documentation
- `SERVER_SETUP.md` - External server configuration
- `app_config.yaml` - Application settings
- `app.spec` - Build configuration

### Scripts
- `test_build.sh` - Environment testing
- `build_script.sh` - Application building
- `create_dmg.sh` - Installer creation
- `setup_autostart.sh` - Autostart setup
- `full_build.sh` - Complete process

## Notes

### Architecture
- Optimized for Apple Silicon (ARM64)
- Requires macOS 12.0+ for M1/M2 support
- No Intel x86_64 support

### Dependencies
- PyAudio replaced with sounddevice
- Native macOS APIs (Quartz, AppKit)
- Optimized for performance

### Security
- Network access for gRPC
- Local file system access
- System automation permissions


