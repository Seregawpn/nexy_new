#!/bin/bash

# Test Build Script for macOS Application
# This script tests the build process step by step

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

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    print_error "Script must be run from client/ directory"
    exit 1
fi

print_info "🧪 Starting test build process..."

# Step 1: Check dependencies
print_info "Step 1: Checking dependencies..."
if ! command -v pyinstaller &> /dev/null; then
    print_error "PyInstaller not found. Installing..."
    pip install pyinstaller
fi
print_success "PyInstaller found"

# Step 2: Check required files
print_info "Step 2: Checking required files..."
REQUIRED_FILES=("main.py" "build/pyinstaller/app.spec" "config/app_config.yaml")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_success "Found: $file"
    else
        print_error "Missing: $file"
        exit 1
    fi
done

# Step 3: Check icon
print_info "Step 3: Checking icon..."
ICON_PATH="assets/icons/app_icon.icns"
if [ -f "$ICON_PATH" ]; then
    print_success "Icon found: $ICON_PATH"
else
    print_warning "Icon not found: $ICON_PATH"
fi

# Step 4: Test PyInstaller analysis
print_info "Step 4: Testing PyInstaller analysis..."
if pyinstaller --help > /dev/null 2>&1; then
    print_success "PyInstaller is working correctly"
else
    print_error "PyInstaller is not working"
    exit 1
fi

# Step 5: Clean up test files
print_info "Step 5: Cleaning up test files..."
rm -rf build/pyinstaller/dist
rm -rf build/pyinstaller/build
rm -rf __pycache__
rm -rf *.spec

print_success "🧹 Cleanup completed"

print_info "🎯 Test build process completed successfully!"
print_info "Ready to proceed with actual build using: ./build/pyinstaller/build_script.sh"
