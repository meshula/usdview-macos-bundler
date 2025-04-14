# Design Document: Bundling `usdview` as a macOS App

## Objective
Create a macOS `.app` bundle for `usdview` that supports both ARM and x64 architectures. The bundle should be self-contained, with separate runtime environments per architecture, and capable of launching via GUI or CLI.

## Requirements
- macOS `.app` bundle structure
- Dual-architecture support (ARM64 and x86_64)
- Bundled USD libraries and plugins
- Bundled minimal Python environment per architecture
- Self-contained dynamic libraries with proper `@loader_path` fixups
- GUI-based file selection fallback when launched without arguments

## Bundle Layout
```
usdview.app/
└── Contents/
    ├── MacOS/
    │   └── usdview-launcher
    ├── Resources/
    │   ├── icon.icns
    │   ├── ARM/
    │   │   ├── usd/
    │   │   └── python/
    │   └── x64/
    │       ├── usd/
    │       └── python/
    └── Info.plist
```

## Build Steps

### 1. Environment Preparation
Define build root and output layout, with dedicated directories for ARM and x64 builds.

### 2. Building USD
Use `build_usd.py` to compile USD twice:
- Once for ARM64 using a native conda env
- Once for x86_64 using an x64 conda env under Rosetta

### 3. Minimal Python Environments
Use `conda-pack` or similar to bundle only necessary Python packages per architecture into:
- `Resources/ARM/python/`
- `Resources/x64/python/`

### 4. USD Binaries and Plugins
Copy relevant binaries, shared libraries, and plugins into:
- `Resources/ARM/usd/`
- `Resources/x64/usd/`

### 5. Dynamic Library Fixups
Use `otool -L` to discover dependencies recursively. Use `install_name_tool` to rewrite paths:
- Change all absolute paths to use `@loader_path`
- Ensure internal consistency within each architecture's runtime

### 6. Launcher Program
Create a small binary (`usdview-launcher`) that:
- Detects system architecture via `uname -m` or `arch`
- Checks if the user passed a file argument
  - If so, runs the appropriate `python usdview <file>`
  - If not, pops a file open dialog via Cocoa or AppleScript

### 7. Plist and Icon
Create a valid `Info.plist`:
- `CFBundleExecutable` -> `usdview-launcher`
- `CFBundleIconFile` -> `icon.icns`
- `CFBundleIdentifier`, `CFBundleName`, etc.

Provide a 512x512 `.icns` file for branding.

## Optional Improvements
- Add version metadata to `Info.plist`
- Support drag-and-drop onto the app icon
- Add custom About panel in the app bundle

## Summary
This design will produce a single `.app` bundle compatible with both Apple Silicon and Intel Macs. The app will function whether launched interactively or from the CLI, and will maintain total runtime independence with all dylibs and scripts quarantined per architecture.