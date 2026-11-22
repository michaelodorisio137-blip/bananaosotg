#!/usr/bin/env python3
"""Apply RG DS speed-biased Android defaults to a pinned Dolphin source checkout.

The changes affect only fresh Dolphin settings in this custom app ID. Every
replacement is verified so a changed upstream source fails instead of silently
producing a stock Dolphin APK.
"""
from pathlib import Path
import sys


def replace_once(source: str, old: str, new: str, path: str) -> str:
    occurrences = source.count(old)
    if occurrences != 1:
        raise RuntimeError(
            f"{path}: expected exactly one occurrence of {old!r}, found {occurrences}"
        )
    return source.replace(old, new, 1)


def main(root: Path) -> None:
    edits = {
        "Source/Core/Core/Config/MainSettings.cpp": [
            (
                'MAIN_OVERCLOCK{{System::Main, "Core", "Overclock"}, 1.0f}',
                'MAIN_OVERCLOCK{{System::Main, "Core", "Overclock"}, 0.75f}',
            ),
            (
                'MAIN_OVERCLOCK_ENABLE{{System::Main, "Core", "OverclockEnable"}, false}',
                'MAIN_OVERCLOCK_ENABLE{{System::Main, "Core", "OverclockEnable"}, true}',
            ),
        ],
        "Source/Core/Core/Config/GraphicsSettings.cpp": [
            (
                '{System::GFX, "Settings", "SafeTextureCacheColorSamples"}, 128}',
                '{System::GFX, "Settings", "SafeTextureCacheColorSamples"}, 0}',
            ),
            (
                '{System::GFX, "Settings", "EnableGPUTextureDecoding"}, false}',
                '{System::GFX, "Settings", "EnableGPUTextureDecoding"}, true}',
            ),
            (
                '"ShaderCompilationMode"}, ShaderCompilationMode::Synchronous}',
                '"ShaderCompilationMode"}, ShaderCompilationMode::AsynchronousSkipRendering}',
            ),
            (
                '"MaxAnisotropy"}, AnisotropicFilteringMode::Default}',
                '"MaxAnisotropy"}, AnisotropicFilteringMode::Force2x}',
            ),
            (
                'GFX_HACK_VI_SKIP{{System::GFX, "Hacks", "VISkip"}, false}',
                'GFX_HACK_VI_SKIP{{System::GFX, "Hacks", "VISkip"}, true}',
            ),
        ],
        "Source/Android/app/build.gradle.kts": [
            (
                'applicationId = "org.dolphinemu.dolphinemu"',
                'applicationId = "org.rgds.dolphinspeed"',
            ),
            (
                'abiFilters += listOf("arm64-v8a", "x86_64")',
                'abiFilters += listOf("arm64-v8a")',
            ),
            ('"Dolphin Emulator")', '"RG DS Dolphin Speed")'),
            ('"Dolphin Debug")', '"RG DS Dolphin Speed (Test)")'),
            ('"-DCMAKE_BUILD_TYPE=RelWithDebInfo"', '"-DCMAKE_BUILD_TYPE=Release"'),
        ],
        "Source/Android/app/src/main/res/values/strings.xml": [
            (
                '<string name="app_name">Dolphin Emulator</string>',
                '<string name="app_name">RG DS Dolphin Speed</string>',
            ),
        ],
    }

    # Validate ALL replacements before modifying files.
    patched = {}
    for relative, substitutions in edits.items():
        path = root / relative
        original = path.read_text(encoding="utf-8")
        changed = original
        for old, new in substitutions:
            # Compatibility entry for old upstream source is intentionally absent.
            changed = replace_once(changed, old, new, relative)
        patched[path] = changed

    for path, content in patched.items():
        path.write_text(content, encoding="utf-8")
        print(f"Patched {path.relative_to(root)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: patch_rgds_dolphin.py PATH_TO_DOLPHIN")
    main(Path(sys.argv[1]).resolve())
