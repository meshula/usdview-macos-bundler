# Design Document: USD Viewer Bundler

## Objective
Create a Python-based tool to bundle `usdview` as a macOS `.app` with support for both ARM and x64 architectures. The bundle should be self-contained, with separate runtime environments per architecture, and capable of launching via GUI or CLI.

## Architecture Overview
The bundler follows a modular, object-oriented design with clean separation of concerns:

```
usdview_bundler/
├── __init__.py
├── bundler.py         # Main orchestration class
├── builders/
│   ├── __init__.py
│   ├── usd_builder.py    # Handles USD compilation
│   └── python_env.py     # Manages Python environments
├── packagers/
│   ├── __init__.py
│   ├── app_structure.py  # Creates .app structure
│   └── dylib_fixer.py    # Handles library dependency pathing
├── signing/
│   ├── __init__.py
│   └── notarizer.py      # Handles code signing and notarization
└── utils/
    ├── __init__.py
    ├── arch.py           # Architecture detection utilities
    └── plist.py          # Plist manipulation
```

## Core Components

### Bundler Class
The central orchestrator that coordinates the build process:
- Initializes and configures all components
- Manages the build workflow for each architecture
- Provides both API and CLI interfaces
- Handles configuration and logging

### Builders
Components responsible for building core elements:

#### UsdBuilder
- Builds USD for a specific architecture
- Handles platform-specific environmental setup
- Manages build artifacts and installation

#### PythonEnvironment
- Creates architecture-specific conda environments
- Packages environments for redistribution using dynamic conda-pack installation
- Ensures proper isolation between ARM and x64 Python environments

### Packagers
Components for packaging and preparing the application:

#### AppStructure
- Creates the macOS .app bundle directory structure
- Generates and manages application resources (icons, info.plist)
- Creates the architecture-aware launcher script

#### DylibFixer
- Recursively identifies dynamic library dependencies
- Rewrites library paths using `@loader_path` for proper bundling
- Ensures runtime environment integrity per architecture

### Signing
Components for code signing and distribution:

#### Notarizer
- Handles code signing with Developer ID
- Submits bundles for Apple notarization
- Staples notarization tickets to the bundle

### Utilities
Shared utility components:

#### Architecture
- Detects system architecture
- Provides platform-specific configurations
- Manages Rosetta 2 compatibility checks

#### PlistManager
- Creates and modifies property list files
- Generates application metadata
- Handles file type associations

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

## Workflows

### Development & Testing
1. Configure bundler with build and output directories
2. Create basic app structure with resources
3. For each architecture:
   - Build USD with appropriate configurations
   - Create and package Python environment
   - Fix library dependencies
4. Create launcher script that detects architecture at runtime
5. Test locally without signing

### Distribution Preparation
1. Complete development workflow
2. Sign the app bundle with Developer ID
3. Create signed ZIP for distribution
4. (Optional) Submit for notarization
5. (Optional) Staple notarization ticket

## Key Technical Challenges & Solutions

### Dynamic Library Dependencies
**Challenge:** Ensuring all dynamic libraries use relative paths.

**Solution:** The DylibFixer component recursively:
1. Identifies each library's dependencies with `otool -L`
2. Rewrites IDs with `install_name_tool -id`
3. Updates dependency references with `install_name_tool -change`
4. Uses `@loader_path` for relative paths

### Cross-Architecture Support
**Challenge:** Supporting both ARM and x64 architectures in one bundle.

**Solution:**
1. Maintain separate USD and Python environments per architecture
2. Use a launcher script that detects architecture at runtime
3. Dynamically select the appropriate environment

### Python Environment Packaging
**Challenge:** Creating relocatable Python environments.

**Solution:**
1. Create architecture-specific conda environments
2. Dynamically install and use conda-pack at runtime
3. Package environments as relocatable archives
4. Ensure proper activation/deactivation in the launcher

### App Bundle Structure
**Challenge:** Creating a valid macOS app bundle.

**Solution:**
1. Create standard macOS .app directory structure
2. Generate proper Info.plist with file associations
3. Create appropriate icons and resources
4. Implement architecture-aware launcher

## Future Improvements
1. Add support for incremental builds
2. Implement parallel processing for multi-architecture builds
3. Add a GUI for configuration and monitoring
4. Expand platform support beyond macOS
5. Support for USD plugin extensions