#!/bin/bash

# Autostart Setup Script for macOS Application
# This script helps users set up autostart for the AI Voice Assistant

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

print_header "AUTOSTART SETUP FOR AI VOICE ASSISTANT"

print_info "This script will help you set up autostart for the AI Voice Assistant."
echo ""

# Check if .app file exists
APP_PATH="build/pyinstaller/dist/Nexy.app"
if [ ! -d "$APP_PATH" ]; then
    print_warning "Application not found at: $APP_PATH"
    print_info "Please build the application first using: ./build/pyinstaller/build_script.sh"
    exit 1
fi

print_success "Application found at: $APP_PATH"

# Instructions for manual setup
print_header "MANUAL AUTOSTART SETUP INSTRUCTIONS"

echo "Since macOS requires manual setup for autostart, follow these steps:"
echo ""

print_info "Step 1: Open System Preferences"
echo "   - Click on Apple menu (🍎) → System Preferences"
echo ""

print_info "Step 2: Go to Users & Groups"
echo "   - Click on 'Users & Groups'"
echo ""

print_info "Step 3: Select your user account"
echo "   - Click on your username in the left sidebar"
echo ""

print_info "Step 4: Click on 'Login Items' tab"
echo "   - You'll see a list of applications that start automatically"
echo ""

print_info "Step 5: Add the AI Voice Assistant"
echo "   - Click the '+' button below the list"
echo "   - Navigate to: $APP_PATH"
echo "   - Select 'Nexy.app' and click 'Add'"
echo ""

print_info "Step 6: Enable autostart"
echo "   - Make sure the checkbox next to 'Nexy' is checked"
echo "   - Close System Preferences"
echo ""

print_warning "IMPORTANT NOTES:"
echo "   - The application will start automatically when you log in"
echo "   - It will run in the background (no Dock icon)"
echo "   - You can control it using keyboard shortcuts or voice commands"
echo ""

print_info "Alternative: Quick Launch"
echo "You can also add the application to your Dock for quick access:"
echo "   - Drag and drop $APP_PATH to your Dock"
echo "   - Right-click on the Dock icon → Options → 'Keep in Dock'"
echo ""

print_success "Autostart setup instructions completed!"
print_info "After following these steps, restart your Mac to test autostart."
