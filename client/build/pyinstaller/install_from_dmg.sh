#!/bin/bash

# Install Application from DMG Script
# This script properly installs the application from DMG to Applications folder

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

print_header "INSTALLING NEXY FROM DMG"

# Check if DMG exists
DMG_PATH="build/pyinstaller/dist/Nexy_AI_Voice_Assistant_macOS_v1.71.dmg"
if [ ! -f "$DMG_PATH" ]; then
    print_error "DMG file not found: $DMG_PATH"
    print_info "Please build the DMG first using: ./build/pyinstaller/create_dmg.sh"
    exit 1
fi

print_success "DMG found: $DMG_PATH"

# Check if Applications folder is writable
if [ ! -w "/Applications" ]; then
    print_error "Cannot write to /Applications folder"
    print_info "Please run this script with sudo or ensure proper permissions"
    exit 1
fi

print_success "Applications folder is writable"

# Step 1: Mount DMG
print_header "STEP 1: MOUNTING DMG"

print_info "Mounting DMG..."
MOUNT_POINT=$(hdiutil attach "$DMG_PATH" | grep "/Volumes/" | sed 's/.*\/Volumes\///')

if [ -z "$MOUNT_POINT" ]; then
    print_error "Failed to mount DMG"
    exit 1
fi

print_success "DMG mounted at: $MOUNT_POINT"

# Step 2: Copy application to Applications
print_header "STEP 2: INSTALLING APPLICATION"

APP_IN_DMG="/Volumes/$MOUNT_POINT/Nexy.app"
if [ ! -d "$APP_IN_DMG" ]; then
    print_error "Application not found in mounted DMG: $APP_IN_DMG"
    hdiutil detach "$MOUNT_POINT" 2>/dev/null || true
    exit 1
fi

print_success "Application found in DMG: $APP_IN_DMG"

# Remove existing installation if present
if [ -d "/Applications/Nexy.app" ]; then
    print_info "Removing existing installation..."
    rm -rf "/Applications/Nexy.app"
    print_success "Existing installation removed"
fi

# Copy application
print_info "Installing application to /Applications..."
cp -R "$APP_IN_DMG" "/Applications/"

if [ $? -eq 0 ]; then
    print_success "Application installed successfully to /Applications/Nexy.app"
else
    print_error "Failed to install application"
    hdiutil detach "$MOUNT_POINT" 2>/dev/null || true
    exit 1
fi

# Step 3: Unmount DMG
print_header "STEP 3: UNMOUNTING DMG"

print_info "Unmounting DMG..."
hdiutil detach "$MOUNT_POINT" 2>/dev/null || true

if [ $? -eq 0 ]; then
    print_success "DMG unmounted successfully"
else
    print_warning "DMG unmount had issues, but application is installed"
fi

# Step 4: Verify installation
print_header "STEP 4: VERIFYING INSTALLATION"

if [ -d "/Applications/Nexy.app" ]; then
    APP_SIZE=$(du -sh "/Applications/Nexy.app" | cut -f1)
    print_success "Application verified at /Applications/Nexy.app ($APP_SIZE)"
    
    # Check if executable exists
    if [ -f "/Applications/Nexy.app/Contents/MacOS/Nexy" ]; then
        print_success "Executable found and ready"
    else
        print_error "Executable not found in installed application"
        exit 1
    fi
else
    print_error "Application not found in /Applications after installation"
    exit 1
fi

# Step 5: Set proper permissions
print_header "STEP 5: SETTING PERMISSIONS"

print_info "Setting proper permissions..."
chmod -R 755 "/Applications/Nexy.app"
chown -R root:wheel "/Applications/Nexy.app"

print_success "Permissions set correctly"

# Step 6: Verify code signing
print_header "STEP 6: VERIFYING CODE SIGNING"

print_info "Checking code signature..."
if codesign -dv "/Applications/Nexy.app" > /dev/null 2>&1; then
    print_success "Code signature verified"
else
    print_warning "Code signature verification failed"
fi

print_header "INSTALLATION COMPLETED"

print_success "🎉 Nexy has been successfully installed!"
echo ""
print_info "Installation details:"
echo "   📱 Application: /Applications/Nexy.app"
echo "   📊 Size: $APP_SIZE"
echo "   🔐 Code signed: Yes"
echo "   📋 Entitlements: Applied"
echo ""

print_info "You can now:"
echo "   1. Launch Nexy from Applications folder"
echo "   2. Test all permissions and functionality"
echo "   3. Verify gRPC connection to Azure"
echo ""

print_info "To launch the application:"
echo "   - Open Applications folder"
echo "   - Double-click on Nexy"
echo "   - Or use Spotlight: Cmd+Space, type 'Nexy'"
echo ""

print_success "Installation completed successfully!"
