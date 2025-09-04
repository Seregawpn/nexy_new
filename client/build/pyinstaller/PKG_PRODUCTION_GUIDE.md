# PKG Production Guide - Professional Distribution

## Overview
This guide explains how to create, sign, and notarize a PKG installer for professional distribution of the Nexy AI Voice Assistant.

## 🎯 What We're Building

A **PKG installer** is the professional standard for macOS application distribution. It provides:
- ✅ **Professional installation experience**
- ✅ **Automatic placement in Applications folder**
- ✅ **Code signing with Developer ID**
- ✅ **Apple notarization for Gatekeeper compatibility**
- ✅ **Easy distribution to users**

## 📋 Prerequisites

### **Required Tools:**
1. **Xcode Command Line Tools** (latest version)
2. **Developer ID Application Certificate**
3. **Apple ID with app-specific password**

### **Install Xcode Command Line Tools:**
```bash
xcode-select --install
```

### **Check Developer ID:**
```bash
security find-identity -v -p codesigning
```

### **Set Apple ID Password:**
```bash
export APPLE_ID_PASSWORD='your-app-specific-password'
```

**Get app-specific password from:** https://appleid.apple.com/account/manage

## 🚀 Quick Start

### **Option 1: Full Automated Process**
```bash
./build/pyinstaller/build_production_pkg.sh
```

This script will:
1. ✅ Create PKG installer
2. ✅ Sign with Developer ID
3. ✅ Notarize with Apple
4. ✅ Verify everything

### **Option 2: Step-by-Step Process**
```bash
# Step 1: Create PKG
./build/pyinstaller/create_pkg.sh

# Step 2: Sign PKG
./build/pyinstaller/sign_pkg.sh

# Step 3: Notarize PKG
./build/pyinstaller/notarize_pkg.sh
```

## 📁 Generated Files

After successful build, you'll have:

```
build/pyinstaller/dist/
├── Nexy_AI_Voice_Assistant_v1.71.pkg    # Final signed PKG
├── Nexy_AI_Voice_Assistant_macOS_v1.71.dmg  # DMG (alternative)
└── Nexy.app                              # Application bundle
```

## 🔐 Code Signing Process

### **What Happens:**
1. **Component PKG Creation** - Creates installable component
2. **Distribution XML** - Defines installation behavior
3. **Final PKG Assembly** - Combines everything
4. **Developer ID Signing** - Signs with your certificate
5. **Signature Verification** - Ensures integrity

### **Developer ID Requirements:**
- Valid Apple Developer account
- Developer ID Application certificate
- Certificate must be in Keychain

## ✅ Notarization Process

### **What is Notarization:**
- Apple verifies your software is safe
- Removes Gatekeeper warnings
- Required for distribution outside App Store

### **Notarization Steps:**
1. **Submit to Apple** - Upload PKG for verification
2. **Wait for Processing** - Usually 5-15 minutes
3. **Verify Status** - Check approval
4. **Staple Ticket** - Attach approval to PKG
5. **Validate** - Ensure everything works

### **Notarization Requirements:**
- Code signed with Developer ID
- No malicious code
- Follows Apple guidelines
- Valid Apple ID credentials

## 🧪 Testing Your PKG

### **Test Installation:**
```bash
# Install on current system
sudo installer -pkg "build/pyinstaller/dist/Nexy_AI_Voice_Assistant_v1.71.pkg" -target /

# Verify installation
ls -la /Applications/Nexy.app
```

### **Test on Clean System:**
1. Create new user account
2. Install PKG as that user
3. Verify all permissions work
4. Test application functionality

## 📤 Distribution

### **Upload to Website:**
1. Upload PKG to your server
2. Provide download link
3. Include installation instructions

### **User Installation:**
1. Download PKG file
2. Double-click to install
3. Follow installation wizard
4. Application appears in Applications folder

### **Installation Instructions for Users:**
```
Nexy AI Voice Assistant - Installation Guide

1. Download the PKG file
2. Double-click the downloaded file
3. Follow the installation wizard
4. Enter your administrator password when prompted
5. The application will be installed in your Applications folder
6. Launch Nexy from Applications

Note: This installer is code signed and notarized by Apple for your security.
```

## 🔧 Troubleshooting

### **Common Issues:**

#### **"pkgbuild not found"**
```bash
xcode-select --install
```

#### **"No Developer ID found"**
- Check Apple Developer account
- Ensure certificate is installed
- Verify certificate hasn't expired

#### **"Notarization failed"**
- Check Apple ID credentials
- Ensure app-specific password is correct
- Verify no malicious code in application

#### **"Gatekeeper still blocks"**
- Ensure notarization completed
- Check that ticket was stapled
- Verify PKG is properly signed

### **Debug Commands:**
```bash
# Check PKG signature
pkgutil --check-signature "path/to/package.pkg"

# Verify notarization
xcrun stapler validate "path/to/package.pkg"

# Check entitlements
codesign -dv --entitlements :- "path/to/app.app"
```

## 📊 File Sizes

### **Typical Sizes:**
- **Application Bundle**: ~687MB
- **PKG Installer**: ~650MB
- **DMG Installer**: ~480MB

### **Size Optimization:**
- Remove unnecessary dependencies
- Use compression in PKG
- Consider delta updates

## 🔄 Update Process

### **For New Versions:**
1. Update version numbers in scripts
2. Rebuild application
3. Create new PKG
4. Sign and notarize
5. Distribute to users

### **Version Management:**
- Use semantic versioning (1.71.0)
- Keep old versions for rollback
- Document changes between versions

## 📋 Checklist

### **Before Distribution:**
- [ ] PKG created successfully
- [ ] Code signed with Developer ID
- [ ] Notarized by Apple
- [ ] Tested on clean system
- [ ] All permissions work
- [ ] gRPC connection verified
- [ ] Documentation updated

### **Distribution Ready:**
- [ ] Professional PKG installer
- [ ] Apple verified and trusted
- [ ] Gatekeeper compatible
- [ ] Easy user installation
- [ ] Professional appearance

## 🎉 Success!

Once completed, you'll have:
- ✅ **Professional PKG installer**
- ✅ **Code signed and notarized**
- ✅ **Ready for user distribution**
- ✅ **Apple verified and trusted**
- ✅ **Professional installation experience**

Your users can now install Nexy AI Voice Assistant with confidence, knowing it's been verified by Apple and follows all security best practices.

## 📞 Support

If you encounter issues:
1. Check this guide first
2. Verify all prerequisites
3. Check error messages carefully
4. Ensure certificates are valid
5. Contact Apple Developer Support if needed

---

**Happy distributing! 🚀**
