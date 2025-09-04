#!/bin/bash

# Sign PKG Installer Script
# This script signs the PKG installer with Developer ID for distribution

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

print_header "SIGNING PKG INSTALLER"

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    print_error "Script must be run from client/ directory"
    exit 1
fi

# Check if PKG exists
PKG_PATH="build/pyinstaller/dist/Nexy_AI_Voice_Assistant_v1.71.pkg"
if [ ! -f "$PKG_PATH" ]; then
    print_error "PKG file not found: $PKG_PATH"
    print_info "Please create the PKG first using: ./build/pyinstaller/create_pkg.sh"
    exit 1
fi

print_success "PKG found: $PKG_PATH"

# Check if Developer ID Installer is available (preferred for PKG signing)
print_info "Checking Developer ID Installer availability..."
INSTALLER_ID=$(security find-identity -v | grep "Developer ID Installer" | head -1 | awk '{print $2}' | sed 's/"//g')

if [ -n "$INSTALLER_ID" ]; then
    print_success "Developer ID Installer found: $INSTALLER_ID"
    DEVELOPER_ID="$INSTALLER_ID"
    DEVELOPER_NAME="Installer"
    print_info "Using Developer ID Installer for PKG signing..."
else
    # Fallback to Developer ID Application
    print_info "Developer ID Installer not found, checking Developer ID Application..."
    DEVELOPER_ID=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | awk '{print $2}' | sed 's/"//g')
    
    if [ -z "$DEVELOPER_ID" ]; then
        print_error "No Developer ID certificates found"
        print_info "Please ensure you have a valid Developer ID certificate"
        exit 1
    fi
    
    print_success "Developer ID Application found: $DEVELOPER_ID"
    DEVELOPER_NAME=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | sed 's/.*"Developer ID Application: \(.*\)".*/\1/')
    print_info "Using Developer ID Application for PKG signing..."
fi

# Step 1: Sign the PKG
print_header "STEP 1: SIGNING PKG"

SIGNED_PKG="build/pyinstaller/dist/Nexy_AI_Voice_Assistant_v1.71_Signed.pkg"
print_info "Signing PKG with Developer ID..."

# Determine the correct certificate name based on type
if [[ "$DEVELOPER_NAME" == *"Installer"* ]]; then
    CERT_NAME="Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)"
else
    CERT_NAME="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
fi

print_info "Using certificate: $CERT_NAME"

# Try productsign with the correct certificate
if productsign --sign "$CERT_NAME" "$PKG_PATH" "$SIGNED_PKG" 2>/dev/null; then
    print_success "PKG signed with productsign"
else
    print_error "productsign failed with certificate: $CERT_NAME"
    print_info "Error details:"
    productsign --sign "$CERT_NAME" "$PKG_PATH" "$SIGNED_PKG" 2>&1 || true
    exit 1
fi

if [ $? -eq 0 ]; then
    print_success "PKG signed successfully: $SIGNED_PKG"
else
    print_error "Failed to sign PKG"
    exit 1
fi

# Step 2: Verify signature
print_header "STEP 2: VERIFYING SIGNATURE"

print_info "Verifying PKG signature..."
pkgutil --check-signature "$SIGNED_PKG"

if [ $? -eq 0 ]; then
    print_success "PKG signature verification passed"
else
    print_error "PKG signature verification failed"
    exit 1
fi

# Step 3: Get file sizes
ORIGINAL_SIZE=$(du -sh "$PKG_PATH" | cut -f1)
SIGNED_SIZE=$(du -sh "$SIGNED_PKG" | cut -f1)

print_success "Original PKG size: $ORIGINAL_SIZE"
print_success "Signed PKG size: $SIGNED_SIZE"

# Step 4: Clean up original unsigned PKG
print_header "STEP 3: CLEANING UP"

print_info "Removing unsigned PKG..."
rm "$PKG_PATH"

print_success "Unsigned PKG removed"

# Step 5: Rename signed PKG to final name
print_header "STEP 4: FINALIZING"

FINAL_PKG="build/pyinstaller/dist/Nexy_AI_Voice_Assistant_v1.71.pkg"
print_info "Renaming signed PKG to final name..."

mv "$SIGNED_PKG" "$FINAL_PKG"

if [ $? -eq 0 ]; then
    print_success "Final PKG ready: $FINAL_PKG"
else
    print_error "Failed to rename PKG"
    exit 1
fi

print_header "PKG SIGNING COMPLETED"

print_success "🎉 PKG signed successfully!"
echo ""
print_info "Signed PKG Details:"
echo "   📦 File: $FINAL_PKG"
echo "   📊 Size: $SIGNED_SIZE"
echo "   🔐 Developer ID: $DEVELOPER_NAME"
echo "   🆔 Certificate: $DEVELOPER_ID"
echo "   📱 Version: 1.71.0"
echo ""

print_info "Next steps:"
echo "   1. Notarize the PKG with Apple"
echo "   2. Test installation on clean system"
echo "   3. Distribute to users"
echo ""

print_info "To notarize the PKG:"
echo "   ./build/pyinstaller/notarize_pkg.sh"
echo ""

print_success "PKG signing completed successfully!"
