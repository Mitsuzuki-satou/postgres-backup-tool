#!/usr/bin/env python3
"""
Setup script for PostgreSQL Backup & Restore Tool
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="postgres-backup-tool",
    version="3.0.0",
    author="PostgreSQL Backup Tool Team",
    author_email="admin@example.com",
    description="A comprehensive PostgreSQL backup and restore solution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/postgres-backup-tool",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Database",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "tui": ["rich>=13.0.0", "textual>=0.41.0"],
        "gui": ["PyQt5>=5.15.0"],
        "web": ["fastapi>=0.104.0", "uvicorn>=0.24.0", "jinja2>=3.1.0"],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.9.0",
            "flake8>=6.1.0",
            "mypy>=1.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "postgres-backup=main:main",
            "pgbackup=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.html", "*.css", "*.js", "*.json"],
    },
    zip_safe=False,
    keywords="postgresql backup restore database pg_dump pg_restore",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/postgres-backup-tool/issues",
        "Source": "https://github.com/yourusername/postgres-backup-tool",
        "Documentation": "https://postgres-backup-tool.readthedocs.io/",
    },
)