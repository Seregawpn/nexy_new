#!/bin/bash

echo "========================================"
echo "FIXING HARDENED RUNTIME AND RE-SIGNING"
echo "========================================"

APP_PATH="build/pyinstaller/dist/Nexy.app"
ENTITLEMENTS_FILE="build/pyinstaller/entitlements.plist"

echo "✅ App found: $APP_PATH"
echo "✅ Entitlements found: $ENTITLEMENTS_FILE"

echo ""
echo "STEP 1: REMOVING OLD SIGNATURE"
echo "========================================"
codesign --remove-signature "$APP_PATH"

echo ""
echo "STEP 2: SIGNING WITH HARDENED RUNTIME"
echo "========================================"
codesign --force --deep --sign "Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)" \
    --entitlements "$ENTITLEMENTS_FILE" \
    --options runtime \
    --timestamp \
    "$APP_PATH"

echo ""
echo "STEP 3: VERIFYING SIGNATURE"
echo "========================================"
codesign -dv --verbose=4 "$APP_PATH" | grep -E "(Hardened|Runtime|flags)"

echo ""
echo "STEP 4: VERIFYING APP BUNDLE"
echo "========================================"
codesign --verify --verbose=4 "$APP_PATH"

echo ""
echo "✅ Hardened Runtime fix completed!"
echo "ℹ️  Now you can try notarization again"
