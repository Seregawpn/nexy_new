# -*- mode: python ; coding: utf-8 -*-

"""
PyInstaller spec file for macOS application "AI Voice Assistant"
"""

import sys
from pathlib import Path

# File paths
current_dir = Path.cwd()
icon_path = current_dir / "assets" / "icons" / "app_icon.icns"

# Check icon existence
if not icon_path.exists():
    print(f"⚠️ Icon not found: {icon_path}")
    icon_path = None

# Main settings
a = Analysis(
    [str(current_dir / "main.py")],  # Main file
    pathex=[str(current_dir), str(current_dir.parent)],
    binaries=[],
    datas=[
        # Configuration files
        (str(current_dir / "config"), "config"),
        # Icons and resources
        (str(current_dir / "assets"), "assets"),
        # Proto files for gRPC
        (str(current_dir / "streaming.proto"), "."),
        # Utils
        (str(current_dir / "utils"), "utils"),
        # FLAC support files
        ("/opt/homebrew/bin/flac", "."),  # FLAC binary
    ],
    hiddenimports=[
        # Core modules
        "asyncio",
        "logging",
        "time",
        "sys",
        "pathlib",
        
        # Audio
        "sounddevice",
        "numpy",
        "queue",
        "threading",
        "pydub",
        "pydub.audio_segment",
        "pydub.utils",
        
        # STT
        "speech_recognition",
        
        # UI
        "rich.console",
        "rich.text",
        
        # Input
        "pynput",
        
        # Screen capture
        "PIL",
        "PIL.Image",
        
        # gRPC
        "grpc",
        "grpc.aio",
        "streaming_pb2",
        "streaming_pb2_grpc",
        
        # macOS specific
        "Quartz",
        "AppKit",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
        "jupyter",
        "IPython",
        "notebook",
        "speech_recognition.flac-mac",  # Intel x86_64 binary - not compatible with ARM64
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicate files
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Create executable file
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Nexy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Hide console for macOS application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64",  # Только Apple Silicon для нотаризации
    codesign_identity=None,  # Будет настроено позже
    entitlements_file="build/pyinstaller/entitlements.plist",  # Entitlements для нотаризации
)

# Create .app bundle
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Nexy",
)

# Create .app file
app = BUNDLE(
    coll,
    name="Nexy.app",
    icon=icon_path,
    bundle_identifier="com.nexy.assistant",
    info_plist={
        # Main information
        "CFBundleName": "Nexy",
        "CFBundleDisplayName": "Nexy",
        "CFBundleVersion": "1.70.0",
        "CFBundleShortVersionString": "1.70.0",
        "CFBundlePackageType": "APPL",
        "CFBundleSignature": "????",
        
        # macOS specific settings
        "LSMinimumSystemVersion": "12.0.0",  # macOS 12.0+ (Monterey) - M1+ support
        "NSHighResolutionCapable": True,
        
        # Background mode (hide from Dock)
        "LSUIElement": False,  # Changed to False as in your main.spec
        
        # Permissions
        "NSMicrophoneUsageDescription": "Nexy needs access to your microphone to hear your commands.",
        "NSScreenCaptureUsageDescription": "Nexy needs screen recording access to capture content or control the screen based on your commands.",
        "NSAppleEventsUsageDescription": "Nexy needs to control other apps to execute your commands.",
        "NSAccessibilityUsageDescription": "Nexy needs accessibility permissions to assist you with controlling your computer.",
        
        # Architecture - Apple Silicon ONLY (M1/M2)
        "LSArchitecturePriority": ["arm64"],  # ONLY M1/M2 support, NO Intel
        "LSMinimumSystemVersion": "12.0.0",  # macOS 12.0+ (Monterey) - M1+ only
        
        # Application category
        "LSApplicationCategoryType": "public.app-category.productivity",
        
        # Autostart
        "LSBackgroundOnly": False,
        
        # Additional settings
        "NSRequiresAquaSystemAppearance": False,
        "NSAppTransportSecurity": {
            "NSAllowsArbitraryLoads": True,  # For gRPC connections
        },
        
        # Critical for notarization
        "NSPrincipalClass": "NSApplication",
        "CFBundleDocumentTypes": [],
        "CFBundleURLTypes": [],
        "LSApplicationCategoryType": "public.app-category.productivity",
        
        # Sandbox and security
        "NSSupportsAutomaticTermination": False,
        "NSSupportsSuddenTermination": False,
        
        # ARM64 ONLY restrictions
        "LSRequiresNativeExecution": True,  # Только нативная ARM64 архитектура
    },
)


