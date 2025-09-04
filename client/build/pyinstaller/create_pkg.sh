#!/bin/bash

# Create PKG Installer Script for macOS Application
# This script creates a professional PKG installer with proper signing

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

print_header "CREATING PKG INSTALLER"

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    print_error "Script must be run from client/ directory"
    exit 1
fi

# Check if application exists
APP_PATH="build/pyinstaller/dist/Nexy.app"
if [ ! -d "$APP_PATH" ]; then
    print_error "Application not found: $APP_PATH"
    print_info "Please build the application first using: ./build/pyinstaller/build_script.sh"
    exit 1
fi

print_success "Application found: $APP_PATH"

# Check if pkgbuild is available
if ! command -v pkgbuild &> /dev/null; then
    print_error "pkgbuild not found. This script requires Xcode Command Line Tools."
    print_info "Install with: xcode-select --install"
    exit 1
fi

print_success "pkgbuild found"

# Check if productbuild is available
if ! command -v productbuild &> /dev/null; then
    print_error "productbuild not found. This script requires Xcode Command Line Tools."
    print_info "Install with: xcode-select --install"
    exit 1
fi

print_success "productbuild found"

# Create temporary directory for PKG components
TEMP_DIR="build/pyinstaller/pkg_temp"
print_info "Creating temporary directory: $TEMP_DIR"
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

# Step 1: Create component PKG
print_header "STEP 1: CREATING COMPONENT PKG"

# Prepare minimal scripts directory (only required scripts)
SCRIPTS_DIR="build/pyinstaller/pkg_scripts"
print_info "Preparing minimal scripts directory: $SCRIPTS_DIR"
rm -rf "$SCRIPTS_DIR"
mkdir -p "$SCRIPTS_DIR"

# Copy only necessary scripts (postinstall only)
cp -f "build/pyinstaller/postinstall" "$SCRIPTS_DIR/" 2>/dev/null || true

# Ensure permissions
chmod 755 "$SCRIPTS_DIR"/* 2>/dev/null || true

COMPONENT_PKG="$TEMP_DIR/Nexy_Component.pkg"
print_info "Creating component PKG..."

pkgbuild \
    --component "$APP_PATH" \
    --install-location "/Applications" \
    --identifier "com.nexy.assistant.component" \
    --version "1.71.0" \
    --scripts "$SCRIPTS_DIR" \
    --preserve-xattr \
    "$COMPONENT_PKG"

if [ $? -eq 0 ]; then
    print_success "Component PKG created: $COMPONENT_PKG"
else
    print_error "Failed to create component PKG"
    exit 1
fi

# Step 2: Create distribution XML
print_header "STEP 2: CREATING DISTRIBUTION XML"

DIST_XML="$TEMP_DIR/Distribution.xml"
print_info "Creating distribution XML..."

cat > "$DIST_XML" << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>Nexy AI Voice Assistant</title>
    <organization>com.nexy.assistant</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="true" rootVolumeOnly="true"/>
    <pkg-ref id="com.nexy.assistant.component"/>
    <choices-outline>
        <line choice="com.nexy.assistant.choice"/>
    </choices-outline>
    <choice id="com.nexy.assistant.choice" title="Nexy AI Voice Assistant">
        <pkg-ref id="com.nexy.assistant.component"/>
    </choice>
    <pkg-ref id="com.nexy.assistant.component" version="1.71.0" onConclusion="none">Nexy_Component.pkg</pkg-ref>
</installer-gui-script>
EOF

print_success "Distribution XML created: $DIST_XML"

# Step 3: Create final PKG
print_header "STEP 3: CREATING FINAL PKG"

FINAL_PKG="build/pyinstaller/dist/Nexy_AI_Voice_Assistant_v1.71.pkg"
print_info "Creating final PKG..."

productbuild \
    --distribution "$DIST_XML" \
    --package-path "$TEMP_DIR" \
    --version "1.71.0" \
    --identifier "com.nexy.assistant.installer" \
    "$FINAL_PKG"

if [ $? -eq 0 ]; then
    print_success "Final PKG created: $FINAL_PKG"
else
    print_error "Failed to create final PKG"
    exit 1
fi

# Step 4: Get PKG size
PKG_SIZE=$(du -sh "$FINAL_PKG" | cut -f1)
print_success "PKG size: $PKG_SIZE"

# Step 5: Clean up temporary files
print_header "STEP 4: CLEANING UP"

print_info "Removing temporary files..."
rm -rf "$TEMP_DIR"

print_success "Temporary files cleaned up"

# Step 6: Verify PKG
print_header "STEP 5: VERIFYING PKG"

print_info "Verifying PKG structure..."
pkgutil --expand "$FINAL_PKG" "$TEMP_DIR" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    print_success "PKG verification passed"
    rm -rf "$TEMP_DIR"
else
    print_error "PKG verification failed"
    exit 1
fi

# Step 6: Verify payload entitlements (must contain microphone entitlement)
print_header "STEP 6: VERIFY PAYLOAD ENTITLEMENTS"

TMP_PAY=$(mktemp -d /tmp/nexy_pkg_expand.XXXXXX)
PAY_ROOT=$(mktemp -d /tmp/nexy_pkg_root.XXXXXX)

print_info "Expanding PKG fully to: $TMP_PAY"
if ! pkgutil --expand-full "$FINAL_PKG" "$TMP_PAY" >/dev/null 2>&1; then
    print_error "Failed to expand PKG for payload verification"
    rm -rf "$TMP_PAY" "$PAY_ROOT"
    exit 1
fi

PAYLOAD=$(find "$TMP_PAY" -type f -name Payload | head -n1)
if [ -z "$PAYLOAD" ]; then
    print_error "Payload not found inside expanded PKG"
    rm -rf "$TMP_PAY" "$PAY_ROOT"
    exit 1
fi

print_info "Extracting Payload to: $PAY_ROOT"
(cd "$PAY_ROOT" && cat "$PAYLOAD" | gunzip -dc | cpio -idmu >/dev/null 2>&1)

BIN="$PAY_ROOT/Applications/Nexy.app/Contents/MacOS/Nexy"
if [ ! -f "$BIN" ]; then
    print_error "Extracted binary not found at expected path: $BIN"
    rm -rf "$TMP_PAY" "$PAY_ROOT"
    exit 1
fi

print_info "Checking entitlements on extracted binary..."
if codesign -d --entitlements :- "$BIN" 2>/dev/null | grep -q "com.apple.security.device.audio-input"; then
    print_success "Payload entitlements OK: com.apple.security.device.audio-input present"
else
    print_error "Payload entitlements missing: com.apple.security.device.audio-input"
    rm -rf "$TMP_PAY" "$PAY_ROOT"
    exit 1
fi

# Cleanup temporary payload dirs
rm -rf "$TMP_PAY" "$PAY_ROOT"

print_header "PKG CREATION COMPLETED"

print_success "🎉 PKG Installer created successfully!"
echo ""
print_info "PKG Details:"
echo "   📦 File: $FINAL_PKG"
echo "   📊 Size: $PKG_SIZE"
echo "   🆔 Identifier: com.nexy.assistant.installer"
echo "   📱 Version: 1.71.0"
echo ""

print_info "Next steps:"
echo "   1. Sign the PKG with your Developer ID"
echo "   2. Notarize the PKG with Apple"
echo "   3. Test installation on clean system"
echo "   4. Distribute to users"
echo ""

print_info "To sign the PKG:"
echo "   ./build/pyinstaller/sign_pkg.sh"
echo ""

print_info "To notarize the PKG:"
echo "   ./build/pyinstaller/notarize_pkg.sh"
echo ""

print_success "PKG creation completed successfully!"
