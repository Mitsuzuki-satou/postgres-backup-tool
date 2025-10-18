#!/usr/bin/env python3
"""
Build script for PostgreSQL Backup & Restore Tool binary
Creates standalone executable using PyInstaller
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run command and return result"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result

def clean_build_dirs():
    """Clean previous build directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name}...")
            shutil.rmtree(dir_name)
    
    # Clean Python cache files
    for root, dirs, files in os.walk('.'):
        for d in dirs:
            if d == '__pycache__':
                shutil.rmtree(os.path.join(root, d))

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    run_command([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])

def create_spec_file():
    """Create PyInstaller spec file"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Get the project root directory
ROOT_DIR = Path(SPECPATH).parent

# Analysis of the main script
a = Analysis(
    ['main.py'],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('examples', 'examples'),
    ],
    hiddenimports=[
        'asyncpg',
        'psycopg2',
        'textual',
        'rich',
        'fastapi',
        'uvicorn',
        'jinja2',
        'cryptography',
        'schedule',
        'click',
        'pydantic',
        'aiofiles',
        'websockets',
        'starlette',
        'multipart',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
    ],
    noarchive=False,
)

# Create PYZ archive
pyz = PYZ(a.pure)

# Create EXE
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='postgres-backup-tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    with open('postgres-backup-tool.spec', 'w') as f:
        f.write(spec_content)
    print("Created postgres-backup-tool.spec")

def build_binary():
    """Build the binary using PyInstaller"""
    print("Building binary...")
    run_command([
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--onefile',
        '--name=postgres-backup-tool',
        '--add-data=templates:templates',
        '--add-data=static:static',
        '--add-data=examples:examples',
        '--hidden-import=asyncpg',
        '--hidden-import=psycopg2',
        '--hidden-import=textual',
        '--hidden-import=rich',
        '--hidden-import=fastapi',
        '--hidden-import=uvicorn',
        '--hidden-import=jinja2',
        '--hidden-import=cryptography',
        '--hidden-import=schedule',
        '--hidden-import=click',
        '--hidden-import=pydantic',
        '--hidden-import=aiofiles',
        '--hidden-import=websockets',
        '--hidden-import=starlette',
        '--hidden-import=multipart',
        '--exclude-module=tkinter',
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=scipy',
        '--exclude-module=PIL',
        'main.py'
    ])

def test_binary():
    """Test the created binary"""
    binary_path = Path('dist/postgres-backup-tool')
    if sys.platform == 'win32':
        binary_path = Path('dist/postgres-backup-tool.exe')
    
    if not binary_path.exists():
        print(f"Error: Binary not found at {binary_path}")
        return False
    
    print(f"Testing binary: {binary_path}")
    try:
        result = run_command([str(binary_path), '--help'])
        print("Binary test successful!")
        print("Output:")
        print(result.stdout)
        return True
    except Exception as e:
        print(f"Binary test failed: {e}")
        return False

def create_release_package():
    """Create a release package with binary and documentation"""
    print("Creating release package...")
    
    # Create release directory
    release_dir = Path('release')
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir()
    
    # Copy binary
    binary_name = 'postgres-backup-tool'
    if sys.platform == 'win32':
        binary_name += '.exe'
    
    shutil.copy2(f'dist/{binary_name}', release_dir)
    
    # Copy documentation
    shutil.copy2('README.md', release_dir)
    shutil.copy2('LICENSE', release_dir)
    shutil.copy2('examples/sample-config.conf', release_dir)
    
    # Create usage instructions
    usage_content = '''# PostgreSQL Backup & Restore Tool - Binary Version

## Quick Start

### Linux/macOS
```bash
./postgres-backup-tool --help
./postgres-backup-tool --cli      # Command-line interface
./postgres-backup-tool --tui      # Terminal user interface  
./postgres-backup-tool --web      # Web interface at http://127.0.0.1:8080
./postgres-backup-tool --scheduler # Background scheduler daemon
```

### Windows
```cmd
postgres-backup-tool.exe --help
postgres-backup-tool.exe --cli      # Command-line interface
postgres-backup-tool.exe --tui      # Terminal user interface  
postgres-backup-tool.exe --web      # Web interface at http://127.0.0.1:8080
postgres-backup-tool.exe --scheduler # Background scheduler daemon
```

## Prerequisites

You need PostgreSQL client tools installed:
- Ubuntu/Debian: `sudo apt install postgresql-client`
- CentOS/RHEL: `sudo yum install postgresql` or `sudo dnf install postgresql`
- macOS: `brew install postgresql`
- Windows: Download from PostgreSQL website

## Configuration

The binary will look for configuration in:
1. Environment variables
2. `~/.postgres_backup_config` file
3. Command-line arguments

See README.md for detailed configuration options.

## Features

- **CLI Mode**: Command-line interface for scripting
- **TUI Mode**: Rich terminal interface with dashboard
- **Web Mode**: Modern web interface with dark mode
- **Scheduler Mode**: Background daemon for automated backups

## Support

For issues and documentation, visit:
https://github.com/Mitsuzuki-satou/postgres-backup-tool
'''
    
    with open(release_dir / 'BINARY_USAGE.md', 'w') as f:
        f.write(usage_content)
    
    # Create archive
    archive_name = f'postgres-backup-tool-v3.0-{sys.platform}'
    if sys.platform == 'win32':
        archive_name += '.zip'
        shutil.make_archive(archive_name.replace('.zip', ''), 'zip', 'release')
    else:
        archive_name += '.tar.gz'
        shutil.make_archive(archive_name.replace('.tar.gz', ''), 'gztar', 'release')
    
    print(f"Release package created: {archive_name}")

def main():
    """Main build process"""
    print("🔨 Building PostgreSQL Backup & Restore Tool Binary")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path('main.py').exists():
        print("Error: main.py not found. Please run this script from the project root.")
        sys.exit(1)
    
    # Clean previous builds
    clean_build_dirs()
    
    # Install dependencies
    install_dependencies()
    
    # Create spec file
    create_spec_file()
    
    # Build binary
    build_binary()
    
    # Test binary
    if test_binary():
        print("✅ Build successful!")
        
        # Create release package
        create_release_package()
        
        print("\n🎉 PostgreSQL Backup & Restore Tool binary is ready!")
        print(f"Binary location: dist/postgres-backup-tool{'.exe' if sys.platform == 'win32' else ''}")
        print("\nUsage examples:")
        print("  ./postgres-backup-tool --help")
        print("  ./postgres-backup-tool --cli")
        print("  ./postgres-backup-tool --tui")
        print("  ./postgres-backup-tool --web")
        print("  ./postgres-backup-tool --scheduler")
    else:
        print("❌ Build failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()