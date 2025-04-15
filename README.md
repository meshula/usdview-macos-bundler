# USD View Bundler

A Python-based tool for creating macOS application bundles for USD View. This tool handles the complex process of bundling the USD View application with its dependencies for both ARM (Apple Silicon) and x64 (Intel) architectures.

## Features

- Creates standalone macOS `.app` bundles that work on both Apple Silicon and Intel Macs
- Bundles appropriate Python environment for each architecture
- Properly handles dynamic library dependencies
- Supports code signing and notarization for distribution
- Clean, modular, and extensible Python codebase

## Prerequisites

- macOS 11.0 or higher
- Python 3.7 or higher
- Conda package manager
- Xcode Command Line Tools
- USD build dependencies

## Installation

### System Requirements

Before installation, ensure you have these system dependencies:

- macOS 11.0 or higher
- Xcode Command Line Tools (`xcode-select --install`)
- Conda package manager (Miniconda or Anaconda)
- Administrator privileges (for some operations)

### Package Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/usdview-bundler.git
cd usdview-bundler

# Create and activate a conda environment
conda create --name usdview_bundler python=3.11
conda activate usdview_bundler

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .
```

Alternatively, you can install with all dependencies in one command:

```bash
# For development
pip install -e ".[dev]"

# For runtime dependencies only
pip install -e ".[runtime]"
```

## Basic Usage

### Command Line Interface

```bash
# Basic build
usdview-bundler --build-dir ./build --usd-src-dir /path/to/USD

# Build with notarization
APPLE_ID="your.email@example.com" APPLE_PASSWORD="app-specific-password" \
usdview-bundler --build-dir ./build --usd-src-dir /path/to/USD --notarize
```

### Python API

```python
from pathlib import Path
from usdview_bundler.bundler import Bundler

# Create and configure the bundler
bundler = Bundler(
    build_dir=Path("./build"),
    usd_src_dir=Path("/path/to/USD"),
    output_dir=Path("./dist"),
    archs=["ARM", "x64"],
    notarize=False,
    app_name="usdview"
)

# Build the application
bundler.configure()
bundler.build()
```

## Common Workflows

### 1. Development Iteration (Local Testing)

For rapid development and testing, you can build a simple unsigned bundle:

```bash
# Create a basic build for local testing
usdview-bundler --build-dir ./build --usd-src-dir /path/to/USD --app-name "usdview-dev"
```

This produces an unsigned app bundle that works on your local machine. It's perfect for testing changes quickly without the overhead of signing and notarization.

### 2. Build with Signing (Sharing with Colleagues)

When you need to share the app with colleagues but don't need App Store distribution:

```bash
# Set up signing credentials
export APPLE_TEAM_ID="YOUR_TEAM_ID"

# Build with signing
usdview-bundler --build-dir ./build --usd-src-dir /path/to/USD --app-name "usdview-shared" --sign
```

This creates an app signed with your Developer ID, which allows other users to open the app without security warnings (after right-click opening it once).

Advanced Python example with custom settings:

```python
from pathlib import Path
from usdview_bundler.bundler import Bundler

bundler = Bundler(
    build_dir=Path("./build"),
    usd_src_dir=Path("/path/to/USD"),
    output_dir=Path("./dist"),
    archs=["ARM", "x64"],
    app_name="usdview-team"
)

# Enable signing with custom settings
bundler.notarizer.team_id = "YOUR_TEAM_ID"  
bundler.notarizer.sign_only = True  # Sign but don't notarize

bundler.configure()
bundler.build()
```

### 3. Build with Notarization (App Store Distribution)

For public distribution or App Store submission:

```bash
# Set up notarization credentials
export APPLE_ID="your.email@example.com"
export APPLE_PASSWORD="app-specific-password"
export APPLE_TEAM_ID="YOUR_TEAM_ID"

# Build, sign, and notarize
usdview-bundler --build-dir ./build --usd-src-dir /path/to/USD --notarize
```

This creates a fully signed and notarized app bundle that can be distributed to users. It involves:
1. Building the app bundle
2. Code signing with your Developer ID
3. Submitting to Apple for notarization
4. Stapling the notarization ticket to the app

Note: You need an App-Specific Password for your Apple ID, which you can generate in your Apple ID account settings.

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--build-dir` | Directory for intermediate build files | (required) |
| `--usd-src-dir` | Directory containing USD source code | (required) |
| `--output-dir` | Directory for the final app bundle | Current directory |
| `--archs` | Architectures to support | `["ARM", "x64"]` |
| `--app-name` | Name of the application | `"usdview"` |
| `-n, --notarize` | Enable notarization | `False` |
| `--sign` | Enable signing without notarization | `False` |
| `--force-rebuild` | Force rebuild even if output exists | `False` |

## Environment Variables

| Variable | Description | Required For |
|----------|-------------|-------------|
| `APPLE_ID` | Your Apple ID email | Notarization |
| `APPLE_PASSWORD` | App-specific password | Notarization |
| `APPLE_TEAM_ID` | Your Apple Developer Team ID | Signing & Notarization |

## Advanced Configuration

For advanced configuration, you can create a YAML config file:

```yaml
# config.yaml
app_name: "My USD View"
bundle_id: "com.example.usdview"
version: "1.2.0"
icon_path: "./custom_icon.png"
python_version: "3.9"
extra_packages:
  - numpy
  - scipy
```

And use it with:

```bash
usdview-bundler --build-dir ./build --config ./config.yaml
```

## Troubleshooting

### Common Issues

1. **Dynamic Library Paths**

   If you encounter errors like `dyld: Library not loaded`, the app bundle has issues with dynamic library paths. Try:
   
   ```bash
   # Rebuild with verbose logging
   usdview-bundler --build-dir ./build --verbose
   ```

2. **Signing Issues**

   If code signing fails, verify your Developer ID credentials:
   
   ```bash
   # Check available signing identities
   security find-identity -v -p codesigning
   ```

3. **Notarization Failed**

   Check the notarization status with:
   
   ```bash
   xcrun altool --notarization-info <RequestUUID> -u <your.email@example.com>
   ```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.