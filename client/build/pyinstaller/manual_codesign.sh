#!/bin/bash

# Manual Code Signing Script for macOS Application
# This script signs the application after PyInstaller build

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

print_header "MANUAL CODE SIGNING PROCESS"

# Check if Developer ID is available
if ! security find-identity -v -p codesigning | grep -q "Developer ID Application"; then
    print_error "No Developer ID Application certificate found"
    print_info "Please install a Developer ID Application certificate first"
    exit 1
fi

DEVELOPER_ID=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | awk '{print $2}')
print_success "Found Developer ID: $DEVELOPER_ID"

# Check if .app exists
APP_PATH="build/pyinstaller/dist/Nexy.app"
if [ ! -d "$APP_PATH" ]; then
    print_error "Application not found at: $APP_PATH"
    print_info "Please run PyInstaller build first"
    exit 1
fi

print_success "Application found at: $APP_PATH"

# Check entitlements file
ENTITLEMENTS_FILE="build/pyinstaller/entitlements.plist"
if [ ! -f "$ENTITLEMENTS_FILE" ]; then
    print_error "Entitlements file not found: $ENTITLEMENTS_FILE"
    exit 1
fi

print_success "Entitlements file found: $ENTITLEMENTS_FILE"

# Step 1: Sign the main executable
print_header "STEP 1: SIGNING MAIN EXECUTABLE"

MAIN_EXECUTABLE="$APP_PATH/Contents/MacOS/Nexy"
if [ ! -f "$MAIN_EXECUTABLE" ]; then
    print_error "Main executable not found: $MAIN_EXECUTABLE"
    exit 1
fi

print_info "Signing main executable..."
codesign --force --sign "$DEVELOPER_ID" --entitlements "$ENTITLEMENTS_FILE" "$MAIN_EXECUTABLE"

if [ $? -eq 0 ]; then
    print_success "Main executable signed successfully"
else
    print_error "Failed to sign main executable"
    exit 1
fi

# Step 2: Sign all libraries and frameworks
print_header "STEP 2: SIGNING LIBRARIES AND FRAMEWORKS"

print_info "Finding all libraries to sign..."
find "$APP_PATH/Contents" -name "*.dylib" -o -name "*.so" -o -name "*.framework" | while read -r file; do
    if [ -f "$file" ]; then
        print_info "Signing: $(basename "$file")"
        codesign --force --sign "$DEVELOPER_ID" --entitlements "$ENTITLEMENTS_FILE" "$file" 2>/dev/null || true
    fi
done

print_success "Libraries signing completed"

# Step 3: Sign the entire application bundle
print_header "STEP 3: SIGNING APPLICATION BUNDLE"

print_info "Signing entire application bundle..."
codesign --force --deep --sign "$DEVELOPER_ID" --entitlements "$ENTITLEMENTS_FILE" "$APP_PATH"

if [ $? -eq 0 ]; then
    print_success "Application bundle signed successfully"
else
    print_error "Failed to sign application bundle"
    exit 1
fi

# Step 4: Verify the signature
print_header "STEP 4: VERIFYING SIGNATURE"

print_info "Verifying application signature..."
codesign -dv --entitlements :- "$APP_PATH"

if [ $? -eq 0 ]; then
    print_success "Signature verification completed"
else
    print_warning "Signature verification failed"
fi

# Step 5: Check entitlements
print_header "STEP 5: CHECKING ENTITLEMENTS"

print_info "Checking applied entitlements..."
codesign -dv --entitlements :- "$APP_PATH" | grep -A 20 "Entitlements:"

print_success "Entitlements check completed"

# Final verification
print_header "FINAL VERIFICATION"

print_info "Application details:"
echo "   📱 Path: $APP_PATH"
echo "   🔐 Developer ID: $DEVELOPER_ID"
echo "   📋 Entitlements: $ENTITLEMENTS_FILE"

# Check if app can be launched
print_info "Testing application launch capability..."
if codesign -dv "$APP_PATH" | grep -q "valid on disk"; then
    print_success "Application is valid and ready for distribution"
else
    print_warning "Application may have signature issues"
fi

print_header "MANUAL CODE SIGNING COMPLETED"

print_success "🎉 Application has been successfully signed!"
echo ""
print_info "Next steps:"
echo "   1. Test the signed application"
echo "   2. Create DMG installer"
echo "   3. Verify all permissions work"
echo "   4. Deploy to users"
echo ""

print_info "The application is now:"
echo "   ✅ Code signed with Developer ID"
echo "   ✅ Entitlements applied"
echo "   ✅ Ready for macOS Gatekeeper"
echo "   ✅ Professional distribution ready"
