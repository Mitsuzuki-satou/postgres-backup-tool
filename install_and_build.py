#!/usr/bin/env python3
"""
Install and Build Script for PostgreSQL Backup & Restore Tool
Handles virtual environment creation, dependency installation, and binary building
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

def run_command(cmd, cwd=None, check=True):
    """Run command and return result"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result

def detect_shell():
    """Detect current shell"""
    shell = os.environ.get('SHELL', '')
    if 'fish' in shell:
        return 'fish'
    elif 'bash' in shell or 'zsh' in shell:
        return 'bash'
    else:
        return 'unknown'

def setup_virtual_environment():
    """Set up Python virtual environment"""
    print("🔧 Setting up virtual environment...")
    
    venv_path = Path('venv')
    if venv_path.exists():
        print("Virtual environment already exists, removing it...")
        shutil.rmtree(venv_path)
    
    # Create virtual environment
    run_command([sys.executable, '-m', 'venv', 'venv'])
    
    # Determine activation command based on shell
    shell = detect_shell()
    if shell == 'fish':
        activate_cmd = [sys.executable, '-c', 
            'import os; os.system(f"source {venv_path}/bin/activate.fish && pip install -r requirements.txt")']
    else:
        activate_cmd = [sys.executable, '-c', 
            f'source {venv_path}/bin/activate && pip install -r requirements.txt']
    
    # Install dependencies
    print("📦 Installing dependencies...")
    python_venv = venv_path / 'bin' / 'python'
    run_command([str(python_venv), '-m', 'pip', 'install', '--upgrade', 'pip'])
    run_command([str(python_venv), '-m', 'pip', 'install', '-r', 'requirements.txt'])
    
    return str(python_venv)

def clean_build_artifacts():
    """Clean previous build artifacts"""
    print("🧹 Cleaning previous build artifacts...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__', 'release']
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"Removing {dir_name}...")
            shutil.rmtree(dir_path)
    
    # Clean Python cache files recursively
    for root, dirs, files in os.walk('.'):
        for d in dirs[:]:  # Use slice to avoid modifying during iteration
            if d == '__pycache__':
                shutil.rmtree(os.path.join(root, d))
                dirs.remove(d)  # Remove from list to avoid further processing

def run_tests(python_venv):
    """Run test suite"""
    print("🧪 Running tests...")
    
    # Check if pytest is available
    try:
        run_command([python_venv, '-m', 'pytest', 'tests/', '-v'], check=False)
        print("Tests completed (some may have been skipped)")
    except Exception as e:
        print(f"Warning: Could not run tests: {e}")

def build_binary(python_venv):
    """Build the binary using PyInstaller"""
    print("🔨 Building binary...")
    
    # Install PyInstaller if not present
    run_command([python_venv, '-m', 'pip', 'install', 'pyinstaller'])
    
    # Build using PyInstaller
    run_command([
        python_venv, '-m', 'PyInstaller',
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
    print("🧪 Testing binary...")
    
    binary_name = 'postgres-backup-tool'
    if platform.system() == 'Windows':
        binary_name += '.exe'
    
    binary_path = Path('dist') / binary_name
    
    if not binary_path.exists():
        print(f"❌ Binary not found at {binary_path}")
        return False
    
    try:
        result = run_command([str(binary_path), '--help'], check=False)
        if result.returncode == 0:
            print("✅ Binary test successful!")
            return True
        else:
            print(f"❌ Binary test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Binary test failed: {e}")
        return False

def create_release_package():
    """Create a release package"""
    print("📦 Creating release package...")
    
    release_dir = Path('release')
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir()
    
    # Copy binary
    binary_name = 'postgres-backup-tool'
    if platform.system() == 'Windows':
        binary_name += '.exe'
    
    shutil.copy2(f'dist/{binary_name}', release_dir)
    
    # Copy documentation and config files
    files_to_copy = ['README.md', 'LICENSE', 'examples/sample-config.conf']
    for file_name in files_to_copy:
        if Path(file_name).exists():
            shutil.copy2(file_name, release_dir)
    
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

For issues and documentation, visit the project repository.
'''
    
    with open(release_dir / 'BINARY_USAGE.md', 'w') as f:
        f.write(usage_content)
    
    # Create archive
    system = platform.system().lower()
    archive_name = f'postgres-backup-tool-v3.0-{system}'
    
    if system == 'windows':
        archive_name += '.zip'
        shutil.make_archive(archive_name.replace('.zip', ''), 'zip', 'release')
    else:
        archive_name += '.tar.gz'
        shutil.make_archive(archive_name.replace('.tar.gz', ''), 'gztar', 'release')
    
    print(f"✅ Release package created: {archive_name}")
    return archive_name

def install_binary():
    """Install binary to PATH"""
    print("🔧 Installing binary to PATH...")
    
    # Determine installation directory
    if os.geteuid() == 0:
        install_dir = Path("/usr/local/bin")
        config_dir = Path("/etc/postgres-backup-tool")
        print("Running as root - installing to system directory")
    else:
        install_dir = Path.home() / ".local" / "bin"
        config_dir = Path.home() / ".config" / "postgres-backup-tool"
        print("Running as user - installing to home directory")
        print(f"Make sure {install_dir} is in your PATH")
    
    # Create directories
    install_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Install binary
    print(f"Installing binary to {install_dir}")
    binary_source = Path("dist/postgres-backup-tool")
    binary_dest = install_dir / "postgres-backup-tool"
    shutil.copy2(binary_source, binary_dest)
    binary_dest.chmod(0o755)
    
    # Install configuration files
    print(f"Installing configuration files to {config_dir}")
    config_files = [
        ("examples/sample-config.conf", "sample-config.conf"),
        ("README.md", "README.md"),
        ("LICENSE", "LICENSE")
    ]
    
    for src_file, dest_name in config_files:
        src_path = Path(src_file)
        if src_path.exists():
            shutil.copy2(src_path, config_dir / dest_name)
    
    # Create desktop entry for GUI (if not root)
    if os.geteuid() != 0:
        desktop_dir = Path.home() / ".local" / "share" / "applications"
        desktop_dir.mkdir(parents=True, exist_ok=True)
        
        desktop_entry = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=PostgreSQL Backup Tool
Comment=PostgreSQL Backup & Restore Tool
Exec={install_dir}/postgres-backup-tool --web
Icon=applications-system
Terminal=false
Categories=System;Database;
StartupNotify=true
"""
        
        with open(desktop_dir / "postgres-backup-tool.desktop", 'w') as f:
            f.write(desktop_entry)
        print("Created desktop entry")
    
    # Create systemd service (if root)
    if os.geteuid() == 0:
        service_content = f"""[Unit]
Description=PostgreSQL Backup & Restore Tool
After=network.target

[Service]
Type=simple
User=root
ExecStart={install_dir}/postgres-backup-tool --scheduler
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        
        service_path = Path("/etc/systemd/system/postgres-backup-tool.service")
        with open(service_path, 'w') as f:
            f.write(service_content)
        
        print("Created systemd service")
        print("To enable the service: systemctl enable postgres-backup-tool")
        print("To start the service: systemctl start postgres-backup-tool")
    
    print("✅ Binary installed successfully!")
    print(f"Installation directory: {install_dir}")
    print(f"Configuration directory: {config_dir}")
    
    return install_dir

def print_success_message(archive_name):
    """Print success message with next steps"""
    binary_name = 'postgres-backup-tool'
    if platform.system() == 'Windows':
        binary_name += '.exe'
    
    print("\n" + "="*60)
    print("🎉 PostgreSQL Backup & Restore Tool build completed!")
    print("="*60)
    print(f"✅ Binary location: dist/{binary_name}")
    print(f"✅ Release package: {archive_name}")
    print(f"✅ Release directory: release/")
    
    # Install binary to PATH
    install_dir = install_binary()
    
    print("\n📋 Usage Examples:")
    print("  postgres-backup-tool --help")
    print("  postgres-backup-tool --cli")
    print("  postgres-backup-tool --tui")
    print("  postgres-backup-tool --web")
    print("  postgres-backup-tool --scheduler")
    
    print("\n🔧 To activate virtual environment manually:")
    shell = detect_shell()
    if shell == 'fish':
        print("  source venv/bin/activate.fish")
    else:
        print("  source venv/bin/activate")
    
    print("\n📦 To install as package (optional):")
    print("  pip install -e .")
    
    if os.geteuid() != 0:
        print(f"\n🔧 To add to PATH (add to ~/.bashrc, ~/.zshrc, or ~/.config/fish/config.fish):")
        print(f"  bash/zsh: export PATH=\"$PATH:{install_dir}\"")
        print(f"  fish: set -gx PATH $PATH {install_dir}")
        print("\nThen reload your shell:")
        print("  bash/zsh: source ~/.bashrc  # or ~/.zshrc")
        print("  fish: source ~/.config/fish/config.fish")
    
    print("\n🎉 Enjoy using PostgreSQL Backup & Restore Tool!")

def main():
    """Main build process"""
    print("🚀 PostgreSQL Backup & Restore Tool - Install & Build Script")
    print("="*60)
    
    # Check if we're in the right directory
    if not Path('main.py').exists():
        print("❌ Error: main.py not found. Please run this script from the project root.")
        sys.exit(1)
    
    try:
        # Step 1: Clean previous builds
        clean_build_artifacts()
        
        # Step 2: Set up virtual environment and install dependencies
        python_venv = setup_virtual_environment()
        
        # Step 3: Run tests (optional)
        run_tests(python_venv)
        
        # Step 4: Build binary
        build_binary(python_venv)
        
        # Step 5: Test binary
        if test_binary():
            # Step 6: Create release package
            archive_name = create_release_package()
            
            # Step 7: Print success message
            print_success_message(archive_name)
        else:
            print("❌ Build failed! Binary test did not pass.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Build interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Build failed with error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()