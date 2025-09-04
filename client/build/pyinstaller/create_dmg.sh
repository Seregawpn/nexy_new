#!/bin/bash

# DMG Creator Script for macOS Application
# This script creates a DMG installer with automatic installation

set -e  # Stop on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions for output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    print_error "Script must be run from client/ directory"
    exit 1
fi

print_header "DMG INSTALLER CREATION"

# Check if .app file exists
APP_PATH="build/pyinstaller/dist/Nexy.app"
if [ ! -d "$APP_PATH" ]; then
    print_warning "Application not found at: $APP_PATH"
    print_info "Please build the application first using: ./build/pyinstaller/build_script.sh"
    exit 1
fi

print_success "Application found at: $APP_PATH"

# Check if create-dmg is installed
if ! command -v create-dmg &> /dev/null; then
    print_warning "create-dmg not found. Installing..."
    if command -v brew &> /dev/null; then
        brew install create-dmg
    else
        print_error "Homebrew not found. Please install create-dmg manually:"
        print_info "https://github.com/create-dmg/create-dmg"
        exit 1
    fi
fi

print_success "create-dmg found"

# Create DMG
print_info "Creating DMG installer..."
DMG_NAME="Nexy_AI_Voice_Assistant_macOS.dmg"
DMG_PATH="build/pyinstaller/dist/$DMG_NAME"

# Remove existing DMG
if [ -f "$DMG_PATH" ]; then
    rm "$DMG_PATH"
fi

# Create DMG with automatic installation
create-dmg \
    --volname "Nexy AI Voice Assistant" \
    --volicon "assets/icons/app_icon.icns" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "Nexy.app" 175 120 \
    --hide-extension "Nexy.app" \
    --app-drop-link 425 120 \
    --no-internet-enable \
    "$DMG_PATH" \
    "build/pyinstaller/dist/"

if [ -f "$DMG_PATH" ]; then
    DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
    print_success "DMG created successfully!"
    print_info "DMG file: $DMG_PATH"
    print_info "DMG size: $DMG_SIZE"
    
    # Show DMG contents
    print_info "DMG contents:"
    hdiutil info "$DMG_PATH" | grep -E "(image-path|mounted|devnode)" || true
    
else
    print_error "Failed to create DMG"
    exit 1
fi

print_header "INSTALLATION INSTRUCTIONS FOR USERS"

echo "The DMG installer has been created successfully!"
echo ""
print_info "For Blind Users - Installation Steps:"
echo ""
echo "1. Double-click the DMG file: $DMG_NAME"
echo "2. VoiceOver will announce: 'Nexy AI Voice Assistant'"
echo "3. Press Cmd+Shift+G to open 'Go to Folder'"
echo "4. Type: /Applications and press Enter"
echo "5. Drag the 'Nexy' app from the DMG to the Applications folder"
echo "6. VoiceOver will announce the copy progress"
echo "7. Eject the DMG by pressing Cmd+E"
echo ""
print_warning "IMPORTANT: After installation, you need to:"
echo "   - Grant microphone permission when prompted"
echo "   - Grant screen recording permission when prompted"
echo "   - Set up autostart using: ./build/pyinstaller/setup_autostart.sh"
echo ""

print_success "DMG creation completed!"
print_info "DMG file ready for distribution: $DMG_PATH"
