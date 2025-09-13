#!/bin/bash

# Sign and Notarize script for State Management module on macOS
# This script signs the built module and submits it for notarization

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MODULE_NAME="state_management"
BUNDLE_ID="com.nexy.state.management"
APPLE_ID=""
TEAM_ID=""
KEYCHAIN_PROFILE=""

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
DIST_DIR="$MODULE_DIR/macos/dist"

echo -e "${BLUE}🔐 Signing and Notarizing State Management module${NC}"

# Check if required tools are available
echo -e "${BLUE}🔍 Checking required tools...${NC}"

if ! command -v codesign &> /dev/null; then
    echo -e "${RED}❌ codesign not found. Please install Xcode Command Line Tools.${NC}"
    exit 1
fi

if ! command -v xcrun &> /dev/null; then
    echo -e "${RED}❌ xcrun not found. Please install Xcode Command Line Tools.${NC}"
    exit 1
fi

if ! command -v xcrun notarytool &> /dev/null; then
    echo -e "${RED}❌ notarytool not found. Please install Xcode Command Line Tools.${NC}"
    exit 1
fi

# Check if build exists
if [ ! -d "$DIST_DIR" ]; then
    echo -e "${RED}❌ Build directory not found. Please run build_macos.sh first.${NC}"
    exit 1
fi

# Load configuration from notarization config
CONFIG_FILE="$MODULE_DIR/macos/notarization/notarization_config.json"
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${BLUE}📋 Loading configuration from $CONFIG_FILE${NC}"
    APPLE_ID=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['apple_id'])" 2>/dev/null || echo "")
    TEAM_ID=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['team_id'])" 2>/dev/null || echo "")
    KEYCHAIN_PROFILE=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['keychain_profile'])" 2>/dev/null || echo "")
fi

# Prompt for missing configuration
if [ -z "$APPLE_ID" ]; then
    read -p "Enter Apple ID: " APPLE_ID
fi

if [ -z "$TEAM_ID" ]; then
    read -p "Enter Team ID: " TEAM_ID
fi

if [ -z "$KEYCHAIN_PROFILE" ]; then
    read -p "Enter Keychain Profile name: " KEYCHAIN_PROFILE
fi

# Verify configuration
if [ -z "$APPLE_ID" ] || [ -z "$TEAM_ID" ] || [ -z "$KEYCHAIN_PROFILE" ]; then
    echo -e "${RED}❌ Missing required configuration. Please provide Apple ID, Team ID, and Keychain Profile.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Configuration loaded${NC}"
echo "Apple ID: $APPLE_ID"
echo "Team ID: $TEAM_ID"
echo "Keychain Profile: $KEYCHAIN_PROFILE"

# Sign the framework
echo -e "${BLUE}🔐 Signing framework...${NC}"
FRAMEWORK_PATH="$DIST_DIR/StateManagement.framework"

if [ ! -d "$FRAMEWORK_PATH" ]; then
    echo -e "${RED}❌ Framework not found at $FRAMEWORK_PATH${NC}"
    exit 1
fi

# Sign the framework
codesign --force --sign "$TEAM_ID" --timestamp --options runtime "$FRAMEWORK_PATH"

# Verify signature
echo -e "${BLUE}🔍 Verifying signature...${NC}"
codesign --verify --verbose "$FRAMEWORK_PATH"
spctl --assess --verbose "$FRAMEWORK_PATH"

# Sign the package
echo -e "${BLUE}🔐 Signing package...${NC}"
PACKAGE_PATH="$DIST_DIR/StateManagement-1.0.0.pkg"

if [ ! -f "$PACKAGE_PATH" ]; then
    echo -e "${RED}❌ Package not found at $PACKAGE_PATH${NC}"
    exit 1
fi

# Sign the package
productsign --sign "$TEAM_ID" "$PACKAGE_PATH" "$DIST_DIR/StateManagement-1.0.0-signed.pkg"

# Verify package signature
echo -e "${BLUE}🔍 Verifying package signature...${NC}"
pkgutil --check-signature "$DIST_DIR/StateManagement-1.0.0-signed.pkg"

# Submit for notarization
echo -e "${BLUE}📤 Submitting for notarization...${NC}"
xcrun notarytool submit "$DIST_DIR/StateManagement-1.0.0-signed.pkg" \
    --apple-id "$APPLE_ID" \
    --team-id "$TEAM_ID" \
    --password "$KEYCHAIN_PROFILE" \
    --wait

# Staple the notarization
echo -e "${BLUE}📌 Stapling notarization...${NC}"
xcrun stapler staple "$DIST_DIR/StateManagement-1.0.0-signed.pkg"

# Verify notarization
echo -e "${BLUE}🔍 Verifying notarization...${NC}"
xcrun stapler validate "$DIST_DIR/StateManagement-1.0.0-signed.pkg"

# Create final distribution
echo -e "${BLUE}📦 Creating final distribution...${NC}"
cd "$DIST_DIR"

# Create signed archive
tar -czf "StateManagement-1.0.0-macos-signed.tar.gz" StateManagement.framework

# Create checksums for signed files
shasum -a 256 "StateManagement-1.0.0-macos-signed.tar.gz" > "StateManagement-1.0.0-macos-signed.tar.gz.sha256"
shasum -a 256 "StateManagement-1.0.0-signed.pkg" > "StateManagement-1.0.0-signed.pkg.sha256"

# Display results
echo -e "${GREEN}✅ Signing and notarization completed successfully!${NC}"
echo -e "${BLUE}📁 Signed artifacts:${NC}"
echo "  Framework: $FRAMEWORK_PATH (signed)"
echo "  Package: $DIST_DIR/StateManagement-1.0.0-signed.pkg (signed & notarized)"
echo "  Archive: $DIST_DIR/StateManagement-1.0.0-macos-signed.tar.gz (signed)"
echo "  Checksums: $DIST_DIR/*-signed.*.sha256"

# Display file sizes
echo -e "${BLUE}📊 File sizes:${NC}"
ls -lh "$DIST_DIR"/*-signed.* 2>/dev/null || true

# Test installation
echo -e "${BLUE}🧪 Testing installation...${NC}"
if [ -f "$DIST_DIR/StateManagement-1.0.0-signed.pkg" ]; then
    echo "Package is ready for installation:"
    echo "  sudo installer -pkg '$DIST_DIR/StateManagement-1.0.0-signed.pkg' -target /"
fi

echo -e "${GREEN}🎉 State Management module signing and notarization completed!${NC}"
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "1. Test the signed package on a clean macOS system"
echo "2. Upload to your distribution platform"
echo "3. Update your documentation with the new signed package"
