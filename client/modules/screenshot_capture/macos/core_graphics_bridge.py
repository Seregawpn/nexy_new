"""
CoreGraphics-based bridge for high-performance screen capture on macOS.
Encodes screenshots as JPEG with configurable quality and optional resizing.

Requirements (ensure in requirements.txt and PyInstaller hiddenimports):
- pyobjc-core
- pyobjc-framework-Quartz
- pyobjc-framework-Cocoa
"""

import base64
import time
from typing import Any, Dict, Tuple

from AppKit import NSBitmapImageRep, NSImageCompressionFactor, NSBitmapImageFileTypeJPEG
from Quartz import (
    CGMainDisplayID,
    CGDisplayCreateImage,
    CGWindowListCreateImage,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID,
    kCGWindowImageDefault,
    CGBitmapContextCreate,
    CGBitmapContextCreateImage,
    CGColorSpaceCreateDeviceRGB,
    CGContextDrawImage,
    kCGImageAlphaPremultipliedLast,
    CGImageGetWidth,
    CGImageGetHeight,
)

from ..core.types import (
    ScreenshotResult,
    ScreenshotConfig,
    ScreenshotData,
    ScreenshotFormat,
)


class CoreGraphicsBridge:
    """Bridge that uses CoreGraphics to capture screen and encodes to JPEG."""

    def __init__(self) -> None:
        # Preflight could be added here if needed
        pass

    def capture_full_screen(self, config: ScreenshotConfig) -> ScreenshotResult:
        start_ts = time.time()
        cg_image = CGDisplayCreateImage(CGMainDisplayID())
        if not cg_image:
            return ScreenshotResult(success=False, error="CGDisplayCreateImage failed")
        return self._encode_as_jpeg_result(
            cg_image,
            config,
            start_ts,
            meta={"bridge_type": "core_graphics"},
        )

    def capture_region(
        self, region: Tuple[int, int, int, int], config: ScreenshotConfig
    ) -> ScreenshotResult:
        start_ts = time.time()
        x, y, w, h = region
        # Use PyObjC CGRect tuple representation instead of CGRectMake to avoid dlsym/macros issues
        rect = ((x, y), (w, h))
        cg_image = CGWindowListCreateImage(
            rect,
            kCGWindowListOptionOnScreenOnly,
            kCGNullWindowID,
            kCGWindowImageDefault,
        )
        if not cg_image:
            return ScreenshotResult(success=False, error="CGWindowListCreateImage failed")
        return self._encode_as_jpeg_result(
            cg_image,
            config,
            start_ts,
            meta={"bridge_type": "core_graphics_region", "region": region},
        )

    def test_capture(self) -> bool:
        return CGDisplayCreateImage(CGMainDisplayID()) is not None

    def get_screen_info(self) -> Dict[str, Any]:
        return {"bridge_type": "core_graphics"}

    def _encode_as_jpeg_result(
        self, cg_image, config: ScreenshotConfig, start_ts: float, meta: Dict[str, Any]
    ) -> ScreenshotResult:
        target_cg_image = self._resize_if_needed(cg_image, config)
        rep = NSBitmapImageRep.alloc().initWithCGImage_(target_cg_image)

        # Map quality enum/string to compression factor [0.0, 1.0]
        quality_map = {"low": 0.5, "medium": 0.75, "high": 0.85, "maximum": 0.95}
        quality_key = str(getattr(config.quality, "value", config.quality)).lower()
        compression = quality_map.get(quality_key, 0.75)

        nsdata = rep.representationUsingType_properties_(
            NSBitmapImageFileTypeJPEG, {NSImageCompressionFactor: compression}
        )
        blob = bytes(nsdata)
        b64 = base64.b64encode(blob).decode("utf-8")
        width, height = rep.pixelsWide(), rep.pixelsHigh()

        metadata = {
            **meta,
            "timestamp": time.time(),
            "quality": compression,
        }

        return ScreenshotResult(
            success=True,
            data=ScreenshotData(
                base64_data=b64,
                width=width,
                height=height,
                format=ScreenshotFormat.JPEG,
                size_bytes=len(blob),
                mime_type="image/jpeg",
                metadata=metadata,
            ),
            capture_time=time.time() - start_ts,
        )

    def _resize_if_needed(self, cg_image, config: ScreenshotConfig):
        max_w = getattr(config, "max_width", 0) or 0
        max_h = getattr(config, "max_height", 0) or 0

        # Obtain source dimensions
        src_w = int(CGImageGetWidth(cg_image))
        src_h = int(CGImageGetHeight(cg_image))

        if (max_w <= 0 and max_h <= 0) or (
            (max_w <= 0 or src_w <= max_w) and (max_h <= 0 or src_h <= max_h)
        ):
            return cg_image

        scale_w = max_w / src_w if max_w > 0 else 1.0
        scale_h = max_h / src_h if max_h > 0 else 1.0
        scale = min(scale_w, scale_h, 1.0)

        new_w = int(src_w * scale)
        new_h = int(src_h * scale)
        if new_w <= 0 or new_h <= 0:
            return cg_image

        cs = CGColorSpaceCreateDeviceRGB()
        ctx = CGBitmapContextCreate(
            None,
            new_w,
            new_h,
            8,
            new_w * 4,
            cs,
            kCGImageAlphaPremultipliedLast,
        )
        # Use CGRect tuple representation instead of CGRectMake
        CGContextDrawImage(ctx, ((0, 0), (new_w, new_h)), cg_image)
        return CGBitmapContextCreateImage(ctx)


