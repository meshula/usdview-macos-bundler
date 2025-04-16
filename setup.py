#!/usr/bin/env python3
"""
Setup script for usdview_bundler package.
"""

from setuptools import setup, find_packages

setup(
    name="usdview_bundler",
    version="0.1.0",
    description="A Python package for bundling usdview as a macOS application",
    author="Your Name",
    author_email="nporcino@pixar.com",
    packages=find_packages(),
    install_requires=[
        "pyyaml>=6.0",
        "psutil>=5.9.0",
        "rich>=12.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "isort>=5.10.0",
            "mypy>=0.950",
        ],
        "runtime": [
            "PyOpenGL>=3.1.0",
            "PySide6>=6.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "usdview-bundler=usdview_bundler.bundler:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
    ],
    python_requires=">=3.7",
)