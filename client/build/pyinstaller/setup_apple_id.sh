#!/bin/bash

# Setup Apple ID Credentials for Notarization
# This script helps set up Apple ID credentials for PKG notarization

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

print_header "APPLE ID SETUP FOR NOTARIZATION"

print_info "This script will help you set up Apple ID credentials for PKG notarization."
echo ""

print_info "You need an app-specific password from Apple ID."
print_info "Get it from: https://appleid.apple.com/account/manage"
echo ""

print_info "Your Apple ID: seregawpn@gmail.com"
print_info "Your Team ID: 5NKLL2CLB9"
echo ""

# Check if APPLE_ID_PASSWORD is already set
if [ -n "$APPLE_ID_PASSWORD" ]; then
    print_success "APPLE_ID_PASSWORD is already set"
    print_info "Current value: ${APPLE_ID_PASSWORD:0:4}****"
    echo ""
    read -p "Do you want to change it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_success "Using existing APPLE_ID_PASSWORD"
        exit 0
    fi
fi

echo ""
print_info "Enter your app-specific password:"
read -s APPLE_ID_PASSWORD

if [ -z "$APPLE_ID_PASSWORD" ]; then
    print_error "Password cannot be empty"
    exit 1
fi

echo ""
print_info "Testing credentials..."

# Test credentials by trying to store them
if xcrun notarytool store-credentials nexy-profile \
    --apple-id "seregawpn@gmail.com" \
    --team-id "5NKLL2CLB9" \
    --password "$APPLE_ID_PASSWORD" \
    --no-validate 2>/dev/null; then
    
    print_success "Credentials stored successfully!"
    
    # Set environment variable
    export APPLE_ID_PASSWORD="$APPLE_ID_PASSWORD"
    
    print_info "Environment variable set for current session"
    print_info "To make it permanent, add to your shell profile:"
    echo ""
    echo "export APPLE_ID_PASSWORD='$APPLE_ID_PASSWORD'"
    echo ""
    
    print_success "You can now run notarization:"
    echo "   ./build/pyinstaller/notarize_pkg.sh"
    
else
    print_error "Failed to store credentials"
    print_info "Please check your app-specific password"
    print_info "Make sure it's generated from: https://appleid.apple.com/account/manage"
    exit 1
fi

print_header "SETUP COMPLETED"

print_success "Apple ID credentials configured successfully!"
print_info "Ready for PKG notarization!"
