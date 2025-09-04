#!/bin/bash

# Production PKG Build Script
# This script creates, signs, and notarizes a PKG installer for distribution

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

print_header "PRODUCTION PKG BUILD PROCESS"

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    print_error "Script must be run from client/ directory"
    exit 1
fi

# Check prerequisites
print_header "CHECKING PREREQUISITES"

# Check Xcode Command Line Tools
if ! command -v pkgbuild &> /dev/null; then
    print_error "Xcode Command Line Tools not found"
    print_info "Install with: xcode-select --install"
    exit 1
fi

print_success "Xcode Command Line Tools found"

# Check Developer ID
print_info "Checking Developer ID availability..."
DEVELOPER_ID=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | awk '{print $2}' | sed 's/"//g')

if [ -z "$DEVELOPER_ID" ]; then
    print_error "No Developer ID Application found"
    print_info "Please ensure you have a valid Developer ID certificate"
    exit 1
fi

print_success "Developer ID found: $DEVELOPER_ID"

# Check notarytool
if ! xcrun notarytool --help &> /dev/null; then
    print_error "notarytool not found. This script requires Xcode 13+."
    print_info "Please update Xcode Command Line Tools"
    exit 1
fi

print_success "notarytool found"

# Check Apple ID environment variable
if [ -z "$APPLE_ID_PASSWORD" ]; then
    print_warning "APPLE_ID_PASSWORD environment variable not set"
    print_info "Please set it before running notarization:"
    echo "   export APPLE_ID_PASSWORD='your-app-specific-password'"
    echo ""
    print_info "You can get an app-specific password from:"
    echo "   https://appleid.apple.com/account/manage"
    echo ""
    read -p "Do you want to continue without notarization? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    SKIP_NOTARIZATION=true
else
    print_success "Apple ID password configured"
    SKIP_NOTARIZATION=false
fi

print_header "BUILDING PRODUCTION PKG"

# Step 1: Create PKG
print_header "STEP 1: CREATING PKG INSTALLER"

print_info "Creating PKG installer..."
./build/pyinstaller/create_pkg.sh

if [ $? -eq 0 ]; then
    print_success "PKG created successfully"
else
    print_error "PKG creation failed"
    exit 1
fi

# Step 2: Sign PKG
print_header "STEP 2: SIGNING PKG INSTALLER"

print_info "Signing PKG with Developer ID..."
./build/pyinstaller/sign_pkg.sh

if [ $? -eq 0 ]; then
    print_success "PKG signed successfully"
else
    print_error "PKG signing failed"
    exit 1
fi

# Step 3: Notarize PKG (if possible)
if [ "$SKIP_NOTARIZATION" = false ]; then
    print_header "STEP 3: NOTARIZING PKG INSTALLER"
    
    print_info "Notarizing PKG with Apple..."
    print_warning "This process may take 5-15 minutes..."
    
    ./build/pyinstaller/notarize_pkg.sh
    
    if [ $? -eq 0 ]; then
        print_success "PKG notarized successfully"
    else
        print_error "PKG notarization failed"
        print_warning "PKG is still signed and usable, but not notarized"
    fi
else
    print_warning "Skipping notarization (APPLE_ID_PASSWORD not set)"
fi

# Step 4: Final verification
print_header "STEP 4: FINAL VERIFICATION"

PKG_PATH="build/pyinstaller/dist/Nexy_AI_Voice_Assistant_v1.71.pkg"

if [ -f "$PKG_PATH" ]; then
    PKG_SIZE=$(du -sh "$PKG_PATH" | cut -f1)
    print_success "Final PKG size: $PKG_SIZE"
    
    print_info "Verifying PKG signature..."
    pkgutil --check-signature "$PKG_PATH"
    
    if [ $? -eq 0 ]; then
        print_success "PKG signature verification passed"
    else
        print_error "PKG signature verification failed"
        exit 1
    fi
else
    print_error "Final PKG not found"
    exit 1
fi

print_header "PRODUCTION PKG BUILD COMPLETED"

print_success "🎉 Production PKG build completed successfully!"
echo ""
print_info "Final PKG Details:"
echo "   📦 File: $PKG_PATH"
echo "   📊 Size: $PKG_SIZE"
echo "   🔐 Developer ID: $DEVELOPER_ID"
echo "   ✅ Code signed: Yes"
if [ "$SKIP_NOTARIZATION" = false ]; then
    echo "   ✅ Notarized: Yes"
else
    echo "   ⚠️  Notarized: No (skipped)"
fi
echo "   📱 Version: 1.71.0"
echo ""

print_info "Distribution Status:"
if [ "$SKIP_NOTARIZATION" = false ]; then
    echo "   ✅ Ready for professional distribution"
    echo "   ✅ Gatekeeper compatible"
    echo "   ✅ Apple verified"
else
    echo "   ⚠️  Signed but not notarized"
    echo "   ⚠️  Users may see security warnings"
    echo "   ⚠️  Consider notarizing for production"
fi
echo ""

print_info "Next steps:"
echo "   1. Test installation on clean system"
echo "   2. Upload to your website"
echo "   3. Distribute to users"
echo ""

print_info "To test the PKG:"
echo "   ./build/pyinstaller/test_pkg.sh"
echo ""

print_info "To notarize later (if skipped):"
echo "   export APPLE_ID_PASSWORD='your-password'"
echo "   ./build/pyinstaller/notarize_pkg.sh"
echo ""

print_success "Production PKG build completed successfully!"
