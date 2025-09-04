#!/bin/bash

# Full Build Script for macOS Application
# This script performs the complete build process from start to finish

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

print_header "FULL BUILD PROCESS FOR AI VOICE ASSISTANT"

print_info "This script will perform the complete build process:"
echo "1. Test build environment"
echo "2. Build .app file"
echo "3. Create DMG installer"
echo "4. Generate installation instructions"
echo ""

# Step 1: Test build environment
print_header "STEP 1: TESTING BUILD ENVIRONMENT"
./build/pyinstaller/test_build.sh

# Step 2: Build .app file
print_header "STEP 2: BUILDING .APP FILE"
./build/pyinstaller/build_script.sh

# Step 3: Create DMG installer
print_header "STEP 3: CREATING DMG INSTALLER"
./build/pyinstaller/create_dmg.sh

# Step 4: Generate final instructions
print_header "STEP 4: FINAL INSTRUCTIONS"

print_success "🎉 BUILD PROCESS COMPLETED SUCCESSFULLY!"
echo ""

print_info "Generated files:"
echo "   📱 Application: build/pyinstaller/dist/Nexy.app"
echo "   📦 DMG Installer: build/pyinstaller/dist/Nexy_AI_Voice_Assistant_macOS.dmg"
echo ""

print_info "Next steps:"
echo "   1. Test the .app file on a clean system"
echo "   2. Verify all permissions work correctly"
echo "   3. Test gRPC connection with external server"
echo "   4. Distribute the DMG file to users"
echo ""

print_info "For users:"
echo "   - Run: ./build/pyinstaller/setup_autostart.sh"
echo "   - Follow the installation instructions in the DMG"
echo ""

print_header "BUILD SUMMARY"
echo "✅ Environment tested"
echo "✅ Application built"
echo "✅ DMG installer created"
echo "✅ Instructions generated"
echo ""
print_success "Ready for distribution!"
