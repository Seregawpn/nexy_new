# Certificate Setup for State Management Module

This guide explains how to set up certificates for signing and notarizing the State Management module on macOS.

## Prerequisites

1. **Apple Developer Account** - You need an active Apple Developer Program membership
2. **Xcode** - Install Xcode from the Mac App Store
3. **Command Line Tools** - Install Xcode Command Line Tools

## Step 1: Create Certificates

### 1.1 Developer ID Application Certificate

This certificate is used to sign the application for distribution outside the Mac App Store.

1. Open **Keychain Access**
2. Go to **Keychain Access** → **Certificate Assistant** → **Request a Certificate From a Certificate Authority**
3. Fill in the form:
   - User Email Address: Your Apple ID email
   - Common Name: Your name or organization name
   - CA Email Address: Leave blank
   - Request is: Saved to disk
   - Key Size: 2048 bits
   - Algorithm: RSA
4. Save the certificate request file
5. Go to [Apple Developer Portal](https://developer.apple.com/account/resources/certificates/list)
6. Click **+** to create a new certificate
7. Select **Developer ID Application** and click **Continue**
8. Upload your certificate request file
9. Download the certificate and double-click to install it

### 1.2 Developer ID Installer Certificate

This certificate is used to sign the installer package.

1. Follow the same steps as above
2. Select **Developer ID Installer** instead of **Developer ID Application**
3. Complete the process and install the certificate

## Step 2: Create App-Specific Password

1. Go to [Apple ID Account Page](https://appleid.apple.com/account/manage)
2. Sign in with your Apple ID
3. Go to **Security** section
4. Click **Generate Password** under **App-Specific Passwords**
5. Enter a label like "NotaryTool"
6. Copy the generated password (you'll need it later)

## Step 3: Store Credentials in Keychain

### 3.1 Store App-Specific Password

```bash
# Store the app-specific password
xcrun notarytool store-credentials "notarytool-profile" \
    --apple-id "your-apple-id@example.com" \
    --team-id "YOUR_TEAM_ID" \
    --password "your-app-specific-password"
```

### 3.2 Verify Stored Credentials

```bash
# Test the stored credentials
xcrun notarytool history --apple-id "your-apple-id@example.com" \
    --team-id "YOUR_TEAM_ID" \
    --password "notarytool-profile"
```

## Step 4: Update Configuration

Update the `notarization_config.json` file with your credentials:

```json
{
  "apple_id": "your-apple-id@example.com",
  "team_id": "YOUR_TEAM_ID",
  "keychain_profile": "notarytool-profile",
  "bundle_id": "com.nexy.state.management"
}
```

## Step 5: Test Signing and Notarization

### 5.1 Build the Module

```bash
cd client/state_management
chmod +x macos/scripts/build_macos.sh
./macos/scripts/build_macos.sh
```

### 5.2 Sign and Notarize

```bash
chmod +x macos/scripts/sign_and_notarize.sh
./macos/scripts/sign_and_notarize.sh
```

## Troubleshooting

### Common Issues

1. **Certificate Not Found**
   - Make sure the certificate is installed in your login keychain
   - Check that the certificate is valid and not expired

2. **Invalid Team ID**
   - Verify your Team ID in the Apple Developer Portal
   - Make sure you're using the correct Team ID for your account

3. **Notarization Failed**
   - Check that your app-specific password is correct
   - Verify that the bundle ID matches your Apple Developer account
   - Check the notarization logs for specific error messages

4. **Code Signing Failed**
   - Ensure all required entitlements are present
   - Check that the signing identity is correct
   - Verify that the app bundle is properly structured

### Useful Commands

```bash
# List available certificates
security find-identity -v -p codesigning

# Check certificate details
security find-certificate -c "Developer ID Application" -p | openssl x509 -text

# Verify app signature
codesign --verify --verbose /path/to/your/app

# Check notarization status
xcrun notarytool history --apple-id "your-apple-id@example.com" \
    --team-id "YOUR_TEAM_ID" \
    --password "notarytool-profile"

# Check staple status
xcrun stapler validate /path/to/your/package.pkg
```

## Security Best Practices

1. **Never commit certificates or passwords to version control**
2. **Use environment variables for sensitive information**
3. **Regularly rotate your app-specific passwords**
4. **Keep your certificates secure and backed up**
5. **Use separate certificates for development and production**

## Support

If you encounter issues:

1. Check the [Apple Developer Documentation](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
2. Review the [Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/)
3. Contact Apple Developer Support if needed

## Additional Resources

- [Apple Developer Portal](https://developer.apple.com/account/)
- [Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/)
- [Notarization Documentation](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [Xcode Command Line Tools](https://developer.apple.com/xcode/)
