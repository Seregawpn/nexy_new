
#!/bin/bash

# Notarize PKG Installer Script
# This script notarizes the PKG installer with Apple for distribution

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

print_header "NOTARIZING PKG INSTALLER"

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    print_error "Script must be run from client/ directory"
    exit 1
fi

# Check if PKG exists
PKG_PATH="build/pyinstaller/dist/Nexy_AI_Voice_Assistant_v1.71.pkg"
if [ ! -f "$PKG_PATH" ]; then
    print_error "PKG file not found: $PKG_PATH"
    print_info "Please create and sign the PKG first using:"
    echo "   ./build/pyinstaller/create_pkg.sh"
    echo "   ./build/pyinstaller/sign_pkg.sh"
    exit 1
fi

print_success "PKG found: $PKG_PATH"

# Check if xcrun is available
if ! command -v xcrun &> /dev/null; then
    print_error "xcrun not found. This script requires Xcode Command Line Tools."
    print_info "Install with: xcode-select --install"
    exit 1
fi

print_success "xcrun found"

# Check if notarytool is available
if ! xcrun notarytool --help &> /dev/null; then
    print_error "notarytool not found. This script requires Xcode 13+."
    print_info "Please update Xcode Command Line Tools"
    exit 1
fi

print_success "notarytool found"

# Check if Developer ID is available
print_info "Checking Developer ID availability..."
DEVELOPER_ID=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | awk '{print $2}' | sed 's/"//g')

if [ -z "$DEVELOPER_ID" ]; then
    print_error "No Developer ID Application found"
    print_info "Please ensure you have a valid Developer ID certificate"
    exit 1
fi

print_success "Developer ID found: $DEVELOPER_ID"

# Get Developer ID name
DEVELOPER_NAME=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | awk '{print $3, $4, $5}' | sed 's/"//g')
print_info "Developer: $DEVELOPER_NAME"

# Set Apple ID for notarization
APPLE_ID="seregawpn@gmail.com"
print_info "Apple ID: $APPLE_ID"

# Step 1: Submit for notarization
print_header "STEP 1: SUBMITTING FOR NOTARIZATION"

print_info "Submitting PKG for notarization..."
print_warning "This process may take 2-5 minutes..."

print_info "📤 Starting upload to Apple servers..."
print_info "📊 File size: $(du -sh "$PKG_PATH" | cut -f1)"

# Use JSON output to reliably parse submission id and status
print_info "🔄 Uploading PKG (this may take several minutes)..."
SUBMISSION_JSON=$(xcrun notarytool submit "$PKG_PATH" \
    --keychain-profile "nexy-profile" \
    --team-id "5NKLL2CLB9" \
    --progress \
    --output-format json 2>&1)

UPLOAD_EXIT_CODE=$?

if [ $UPLOAD_EXIT_CODE -ne 0 ]; then
    print_error "❌ Notarization submit command failed (exit code: $UPLOAD_EXIT_CODE)"
    echo "Raw output:"
    echo "$SUBMISSION_JSON"
    exit 1
fi

print_success "✅ Upload completed successfully!"

# Extract id and status from JSON using Python (jq might not be available)
SUBMISSION_ID=$(echo "$SUBMISSION_JSON" | /usr/bin/python3 -c 'import sys,json; print(json.load(sys.stdin).get("id",""))')

print_info "Submission ID: $SUBMISSION_ID"

if [ -z "$SUBMISSION_ID" ]; then
    print_error "Failed to parse submission ID"
    echo "Raw JSON response:"
    echo "$SUBMISSION_JSON"
    exit 1
fi

print_success "✅ PKG submitted successfully!"
print_info "Submission ID: $SUBMISSION_ID"
print_info "⏳ Waiting for Apple to start processing..."

# Wait a bit for processing to start
sleep 10

# Step 2: Check notarization status
print_header "STEP 2: CHECKING NOTARIZATION STATUS"

print_info "🔍 Checking notarization status..."
print_info "📋 This will check status every 30 seconds..."

# Check status multiple times with progress
for i in {1..20}; do
    print_info "📊 Check attempt $i/20..."
    print_info "⏰ Time: $(date '+%H:%M:%S')"
    
    print_info "🔄 Querying Apple servers for status..."
    STATUS_JSON=$(xcrun notarytool info "$SUBMISSION_ID" \
        --keychain-profile "nexy-profile" \
        --team-id "5NKLL2CLB9" \
        --output-format json 2>&1)
    
    STATUS_EXIT_CODE=$?
    
    if [ $STATUS_EXIT_CODE -eq 0 ]; then
        SUBMISSION_STATUS=$(echo "$STATUS_JSON" | /usr/bin/python3 -c 'import sys,json; print(json.load(sys.stdin).get("status",""))')
        
        print_info "📈 Current status: $SUBMISSION_STATUS"
        
        if [ "$SUBMISSION_STATUS" = "Accepted" ]; then
            print_success "🎉 Notarization completed successfully!"
            print_info "✅ Status: ACCEPTED"
            print_info "🎯 Apple has approved your PKG for distribution"
            break
        elif [ "$SUBMISSION_STATUS" = "Invalid" ]; then
            print_error "❌ Notarization failed with status: $SUBMISSION_STATUS"
            print_info "📋 Fetching detailed error log..."
            print_info "🔍 This will show exactly what Apple rejected..."
            
            xcrun notarytool log "$SUBMISSION_ID" \
                --keychain-profile "nexy-profile" \
                --team-id "5NKLL2CLB9"
            exit 1
        elif [ "$SUBMISSION_STATUS" = "In Progress" ]; then
            print_info "⏳ Still processing... waiting 30 seconds"
            print_info "💡 Apple is scanning your PKG for security issues..."
            sleep 30
        elif [ "$SUBMISSION_STATUS" = "Processing" ]; then
            print_info "⚙️ Processing... waiting 30 seconds"
            print_info "🔒 Apple is validating signatures and entitlements..."
            sleep 30
        else
            print_info "📊 Status: $SUBMISSION_STATUS - waiting 30 seconds"
            print_info "⏰ Next check in 30 seconds..."
            sleep 30
        fi
    else
        print_warning "⚠️ Failed to check status (attempt $i), retrying in 30 seconds..."
        print_info "🔍 Exit code: $STATUS_EXIT_CODE"
        print_info "📋 Raw response: $STATUS_JSON"
        sleep 30
    fi
    
    # Show progress bar
    PROGRESS=$((i * 5))
    if [ $PROGRESS -gt 100 ]; then PROGRESS=100; fi
    print_info "📊 Progress: $PROGRESS% complete"
done

# Final status check
if [ "$SUBMISSION_STATUS" != "Accepted" ]; then
    print_error "❌ Notarization did not complete successfully after 20 attempts"
    print_info "📊 Final status: $SUBMISSION_STATUS"
    print_info "⏰ Total time elapsed: ~10 minutes"
    print_info "💡 You can check manually later with:"
    echo "   xcrun notarytool info $SUBMISSION_ID --keychain-profile nexy-profile --team-id 5NKLL2CLB9"
    print_info "📋 Or fetch the detailed log with:"
    echo "   xcrun notarytool log $SUBMISSION_ID --keychain-profile nexy-profile --team-id 5NKLL2CLB9"
    exit 1
fi

# Step 3: Staple notarization ticket
print_header "STEP 3: STAPLING NOTARIZATION TICKET"

print_info "Stapling notarization ticket to PKG..."

xcrun stapler staple "$PKG_PATH"

if [ $? -eq 0 ]; then
    print_success "Notarization ticket stapled successfully"
else
    print_error "Failed to staple notarization ticket"
    exit 1
fi

# Step 4: Verify stapling
print_header "STEP 4: VERIFYING STAPLING"

print_info "Verifying stapling..."

xcrun stapler validate "$PKG_PATH"

if [ $? -eq 0 ]; then
    print_success "Stapling verification passed"
else
    print_error "Stapling verification failed"
    exit 1
fi

# Step 5: Get final file info
print_header "STEP 5: FINAL VERIFICATION"

PKG_SIZE=$(du -sh "$PKG_PATH" | cut -f1)
print_success "Final PKG size: $PKG_SIZE"

print_info "Final PKG verification..."
pkgutil --check-signature "$PKG_PATH"

print_header "NOTARIZATION COMPLETED"

print_success "🎉 PKG notarized successfully!"
echo ""
print_info "Notarized PKG Details:"
echo "   📦 File: $PKG_PATH"
echo "   📊 Size: $PKG_SIZE"
echo "   🔐 Developer ID: $DEVELOPER_NAME"
echo "   🆔 Certificate: $DEVELOPER_ID"
echo "   ✅ Notarized: Yes"
echo "   🎫 Ticket: Stapled"
echo "   📱 Version: 1.71.0"
echo ""

print_info "Next steps:"
echo "   1. Test installation on clean system"
echo "   2. Verify Gatekeeper acceptance"
echo "   3. Distribute to users"
echo ""

print_info "To test the PKG:"
echo "   ./build/pyinstaller/test_pkg.sh"
echo ""

print_info "Distribution ready:"
echo "   ✅ Code signed with Developer ID"
echo "   ✅ Notarized by Apple"
echo "   ✅ Gatekeeper compatible"
echo "   ✅ Ready for user distribution"
echo ""

print_success "PKG notarization completed successfully!"
