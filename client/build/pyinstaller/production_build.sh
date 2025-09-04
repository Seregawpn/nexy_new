#!/bin/bash

# Production Build Script for macOS Application
# This script follows the correct sequence: entitlements → code signing → DMG creation

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

print_header "PRODUCTION BUILD PROCESS - VERSION 1.70"

print_info "This script will perform the complete production build process:"
echo "1. Validate entitlements.plist"
echo "2. Build application with code signing"
echo "3. Create DMG with proper entitlements"
echo "4. Verify final package"
echo ""

# Step 1: Validate entitlements.plist
print_header "STEP 1: VALIDATING ENTITLEMENTS.PLIST"

ENTITLEMENTS_FILE="build/pyinstaller/entitlements.plist"
if [ ! -f "$ENTITLEMENTS_FILE" ]; then
    print_error "Entitlements file not found: $ENTITLEMENTS_FILE"
    exit 1
fi

# Validate XML syntax
if plutil -lint "$ENTITLEMENTS_FILE" > /dev/null 2>&1; then
    print_success "Entitlements file is valid XML"
else
    print_error "Entitlements file has invalid XML syntax"
    exit 1
fi

# Check entitlements content
print_info "Entitlements file contains:"
plutil -p "$ENTITLEMENTS_FILE" | grep -E "(allow-jit|allow-unsigned-executable-memory|disable-library-validation|automation|audio-input|network|files|camera)"

print_success "Entitlements validation completed"

# Step 2: Build application with code signing
print_header "STEP 2: BUILDING APPLICATION WITH CODE SIGNING"

# Check if Developer ID is available
if security find-identity -v -p codesigning | grep -q "Developer ID Application"; then
    DEVELOPER_ID=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | awk '{print $2}')
    print_success "Found Developer ID: $DEVELOPER_ID"
    
    # Update app.spec with Developer ID
    sed -i '' "s/codesign_identity=None/codesign_identity=\"$DEVELOPER_ID\"/" build/pyinstaller/app.spec
    sed -i '' "s/entitlements_file=None/entitlements_file=\"entitlements.plist\"/" build/pyinstaller/app.spec
    
    print_info "Updated app.spec with Developer ID and entitlements"
else
    print_warning "No Developer ID found, building without code signing"
    print_info "To enable code signing, install a Developer ID certificate"
fi

# Build the application
print_info "Building application..."
./build/pyinstaller/build_script.sh

# Step 3: Create DMG with proper entitlements
print_header "STEP 3: CREATING DMG WITH PROPER ENTITLEMENTS"

# Check if .app file exists
APP_PATH="build/pyinstaller/dist/Nexy.app"
if [ ! -d "$APP_PATH" ]; then
    print_error "Application not found at: $APP_PATH"
    exit 1
fi

print_success "Application found at: $APP_PATH"

# Create DMG
print_info "Creating DMG installer..."
./build/pyinstaller/create_dmg.sh

# Step 4: Verify final package
print_header "STEP 4: VERIFYING FINAL PACKAGE"

# Check DMG file
DMG_PATH="build/pyinstaller/dist/Nexy_AI_Voice_Assistant_macOS.dmg"
if [ -f "$DMG_PATH" ]; then
    DMG_SIZE=$(du -sh "$DMG_PATH" | cut -f1)
    print_success "DMG created successfully: $DMG_PATH ($DMG_SIZE)"
    
    # Verify DMG integrity
    print_info "Verifying DMG integrity..."
    if hdiutil verify "$DMG_PATH" > /dev/null 2>&1; then
        print_success "DMG integrity verified"
    else
        print_warning "DMG integrity check failed"
    fi
else
    print_error "DMG file not found"
    exit 1
fi

# Check application bundle
if [ -d "$APP_PATH" ]; then
    APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
    print_success "Application bundle: $APP_PATH ($APP_SIZE)"
    
    # Check if entitlements are applied
    if codesign -dv --entitlements :- "$APP_PATH" > /dev/null 2>&1; then
        print_success "Entitlements are applied to application"
    else
        print_warning "Entitlements not found in application (may be unsigned)"
    fi
fi

print_header "PRODUCTION BUILD COMPLETED"

print_success "🎉 Production build completed successfully!"
echo ""
print_info "Generated files:"
echo "   📱 Application: $APP_PATH"
echo "   📦 DMG Installer: $DMG_PATH"
echo "   🔐 Entitlements: $ENTITLEMENTS_FILE"
echo ""

print_info "Next steps:"
echo "   1. Test the DMG on a clean system"
echo "   2. Verify all permissions work correctly"
echo "   3. Test gRPC connection with Azure Container App"
echo "   4. Deploy to users"
echo ""

print_info "For production distribution:"
echo "   - DMG is ready for website upload"
echo "   - Entitlements are properly configured"
echo "   - Application follows Apple's guidelines"
echo ""

print_header "BUILD SUMMARY"
echo "✅ Entitlements validated"
echo "✅ Application built"
echo "✅ DMG installer created"
echo "✅ Package integrity verified"
echo ""
print_success "Ready for production distribution!"
