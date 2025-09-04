#!/bin/bash

echo "=== NOTARIZING ZIP FILE ==="
echo "ZIP file: build/pyinstaller/dist/Nexy_for_notarization.zip"

echo "Submitting ZIP for notarization..."
echo "This process may take 5-15 minutes..."

SUBMISSION_ID=$(xcrun notarytool submit "build/pyinstaller/dist/Nexy_for_notarization.zip" \
    --keychain-profile "nexy-profile" \
    --team-id "5NKLL2CLB9" \
    --wait)

if [ $? -eq 0 ]; then
    echo "✅ Notarization completed successfully!"
    echo "Submission ID: $SUBMISSION_ID"
else
    echo "❌ Notarization failed"
fi
