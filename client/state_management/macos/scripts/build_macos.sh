#!/bin/bash

# Build script for State Management module on macOS
# This script builds the module as a standalone framework

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MODULE_NAME="state_management"
BUILD_DIR="build"
DIST_DIR="dist"
PYTHON_VERSION="3.12"
ARCHITECTURES="arm64,x86_64"

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
PROJECT_ROOT="$(dirname "$(dirname "$MODULE_DIR")")"

echo -e "${BLUE}🏗️ Building State Management module for macOS${NC}"
echo "Module directory: $MODULE_DIR"
echo "Project root: $PROJECT_ROOT"

# Create build directories
mkdir -p "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Clean previous builds
echo -e "${YELLOW}🧹 Cleaning previous builds...${NC}"
rm -rf "$BUILD_DIR"/*
rm -rf "$DIST_DIR"/*

# Check Python version
echo -e "${BLUE}🐍 Checking Python version...${NC}"
python3 --version

# Install dependencies
echo -e "${BLUE}📦 Installing dependencies...${NC}"
cd "$MODULE_DIR"
pip3 install -r macos/packaging/requirements.txt

# Run tests
echo -e "${BLUE}🧪 Running tests...${NC}"
python3 -m pytest tests/ -v --tb=short

# Create PyInstaller spec file
echo -e "${BLUE}📝 Creating PyInstaller spec...${NC}"
cat > "$BUILD_DIR/state_management.spec" << EOF
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['$MODULE_DIR/__init__.py'],
    pathex=['$MODULE_DIR'],
    binaries=[],
    datas=[
        ('$MODULE_DIR/core', 'core'),
        ('$MODULE_DIR/monitoring', 'monitoring'),
        ('$MODULE_DIR/recovery', 'recovery'),
        ('$MODULE_DIR/config', 'config'),
        ('$MODULE_DIR/utils', 'utils'),
    ],
    hiddenimports=[
        'state_management.core.state_manager',
        'state_management.core.types',
        'state_management.core.state_validator',
        'state_management.monitoring.state_monitor',
        'state_management.recovery.state_recovery',
        'state_management.config.state_config',
        'state_management.utils.state_utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='StateManagement',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='$MODULE_DIR/macos/entitlements/state_management.entitlements',
)

app = BUNDLE(
    exe,
    name='StateManagement.app',
    icon=None,
    bundle_identifier='com.nexy.state.management',
    info_plist='$MODULE_DIR/macos/info/Info.plist',
    version='1.0.0',
    short_version='1.0.0',
    osx_bundle_identifier='com.nexy.state.management',
)
EOF

# Build with PyInstaller
echo -e "${BLUE}🔨 Building with PyInstaller...${NC}"
cd "$BUILD_DIR"
pyinstaller --clean state_management.spec

# Create framework structure
echo -e "${BLUE}📦 Creating framework structure...${NC}"
FRAMEWORK_DIR="$DIST_DIR/StateManagement.framework"
mkdir -p "$FRAMEWORK_DIR/Versions/A/Resources"
mkdir -p "$FRAMEWORK_DIR/Versions/A/Headers"
mkdir -p "$FRAMEWORK_DIR/Versions/A/Modules"

# Copy built app
cp -r "dist/StateManagement.app" "$FRAMEWORK_DIR/Versions/A/Resources/"

# Create framework symlinks
ln -sf "A" "$FRAMEWORK_DIR/Versions/Current"
ln -sf "Versions/Current/Resources" "$FRAMEWORK_DIR/Resources"
ln -sf "Versions/Current/Headers" "$FRAMEWORK_DIR/Headers"
ln -sf "Versions/Current/Modules" "$FRAMEWORK_DIR/Modules"

# Create Info.plist for framework
cat > "$FRAMEWORK_DIR/Resources/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>com.nexy.state.management</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleName</key>
    <string>StateManagement</string>
    <key>CFBundlePackageType</key>
    <string>FMWK</string>
    <key>CFBundleExecutable</key>
    <string>StateManagement</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
</dict>
</plist>
EOF

# Create module map
cat > "$FRAMEWORK_DIR/Headers/module.modulemap" << EOF
framework module StateManagement {
    umbrella header "StateManagement.h"
    export *
    module * { export * }
}
EOF

# Create umbrella header
cat > "$FRAMEWORK_DIR/Headers/StateManagement.h" << EOF
//
//  StateManagement.h
//  StateManagement
//
//  Created by Nexy AI on $(date +%Y-%m-%d).
//

#import <Foundation/Foundation.h>

//! Project version number for StateManagement.
FOUNDATION_EXPORT double StateManagementVersionNumber;

//! Project version string for StateManagement.
FOUNDATION_EXPORT const unsigned char StateManagementVersionString[];

// In this header, you should import all the public headers of your framework using statements like #import <StateManagement/PublicHeader.h>
EOF

# Set version numbers
echo "1.0.0" > "$FRAMEWORK_DIR/Versions/A/Resources/StateManagementVersionNumber"
echo "1.0.0" > "$FRAMEWORK_DIR/Versions/A/Resources/StateManagementVersionString"

# Create distribution package
echo -e "${BLUE}📦 Creating distribution package...${NC}"
cd "$DIST_DIR"
tar -czf "StateManagement-1.0.0-macos.tar.gz" StateManagement.framework

# Create installer package
echo -e "${BLUE}📦 Creating installer package...${NC}"
pkgbuild \
    --root "$FRAMEWORK_DIR" \
    --identifier "com.nexy.state.management" \
    --version "1.0.0" \
    --install-location "/Library/Frameworks" \
    "StateManagement-1.0.0.pkg"

# Sign the package (if code signing is available)
if command -v codesign &> /dev/null; then
    echo -e "${BLUE}🔐 Signing package...${NC}"
    codesign --force --sign - "StateManagement-1.0.0.pkg"
fi

# Create checksums
echo -e "${BLUE}🔍 Creating checksums...${NC}"
shasum -a 256 "StateManagement-1.0.0-macos.tar.gz" > "StateManagement-1.0.0-macos.tar.gz.sha256"
shasum -a 256 "StateManagement-1.0.0.pkg" > "StateManagement-1.0.0.pkg.sha256"

# Display results
echo -e "${GREEN}✅ Build completed successfully!${NC}"
echo -e "${BLUE}📁 Build artifacts:${NC}"
echo "  Framework: $DIST_DIR/StateManagement.framework"
echo "  Archive: $DIST_DIR/StateManagement-1.0.0-macos.tar.gz"
echo "  Package: $DIST_DIR/StateManagement-1.0.0.pkg"
echo "  Checksums: $DIST_DIR/*.sha256"

# Display file sizes
echo -e "${BLUE}📊 File sizes:${NC}"
ls -lh "$DIST_DIR"/*.tar.gz "$DIST_DIR"/*.pkg 2>/dev/null || true

echo -e "${GREEN}🎉 State Management module build completed!${NC}"
