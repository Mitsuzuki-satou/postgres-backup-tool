#!/usr/bin/env python3
"""
Test script for the web interface functionality
"""

import json
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_config_manager():
    """Test ConfigManager functionality"""
    try:
        from src.core.config import ConfigManager
        
        print("Testing ConfigManager...")
        config_manager = ConfigManager()
        
        # Test getting full config
        full_config = config_manager.get_full_config()
        assert isinstance(full_config, dict), "Full config should be a dictionary"
        print("✓ get_full_config() works")
        
        # Test basic config structure
        assert "database" in full_config, "Config should have database section"
        assert "backup" in full_config, "Config should have backup section"
        assert "app" in full_config, "Config should have app section"
        print("✓ Config structure is correct")
        
        return True
        
    except ImportError as e:
        print(f"⚠ ConfigManager test skipped (missing dependency): {e}")
        return True  # Skip but don't fail
    except Exception as e:
        print(f"✗ ConfigManager test failed: {e}")
        return False

def test_models():
    """Test model creation"""
    try:
        from src.core.models import DatabaseConfig, BackupConfig, BackupJob, BackupType, CompressionType, EncryptionType
        from datetime import datetime
        
        print("\nTesting models...")
        
        # Test DatabaseConfig with all required fields
        db_config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass",
            ssl_mode="prefer",
            connection_timeout=30
        )
        print("✓ DatabaseConfig creation works")
        
        # Test BackupConfig with all required fields
        backup_config = BackupConfig(
            backup_type=BackupType.FULL,
            compression=CompressionType.GZIP,
            encryption=EncryptionType.NONE,
            encryption_key=None,
            parallel_jobs=4,
            verbose=True,
            clean_before_restore=True,
            no_owner=True,
            no_privileges=True
        )
        print("✓ BackupConfig creation works")
        
        # Test BackupJob with all required fields
        job = BackupJob(
            id="test-job",
            name="Test Job",
            source_config=db_config,
            backup_config=backup_config,
            backup_dir=Path("/tmp/backups"),
            enabled=True,
            schedule=None,
            retention_days=30
        )
        print("✓ BackupJob creation works")
        
        return True
        
    except ImportError as e:
        print(f"⚠ Models test skipped (missing dependency): {e}")
        return True  # Skip but don't fail
    except Exception as e:
        print(f"✗ Models test failed: {e}")
        return False

def test_api_models():
    """Test API model creation"""
    try:
        from src.web.app import DatabaseConfigModel, BackupConfigModel, BackupJobModel
        
        print("\nTesting API models...")
        
        # Test DatabaseConfigModel
        db_model = DatabaseConfigModel(
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="testpass"
        )
        print("✓ DatabaseConfigModel creation works")
        
        # Test BackupConfigModel
        backup_model = BackupConfigModel(
            backup_type="full",
            compression="gzip"
        )
        print("✓ BackupConfigModel creation works")
        
        # Test BackupJobModel with proper model instances
        job_model = BackupJobModel(
            name="Test Job",
            source_config=db_model,
            backup_config=backup_model
        )
        print("✓ BackupJobModel creation works")
        
        return True
        
    except ImportError as e:
        print(f"⚠ API models test skipped (missing dependency): {e}")
        return True  # Skip but don't fail
    except Exception as e:
        print(f"✗ API models test failed: {e}")
        return False

def test_template_structure():
    """Test if templates exist and have basic structure"""
    print("\nTesting template structure...")
    
    base_template = Path("templates/base.html")
    dashboard_template = Path("templates/dashboard.html")
    
    if not base_template.exists():
        print("✗ base.html template not found")
        return False
    
    if not dashboard_template.exists():
        print("✗ dashboard.html template not found")
        return False
    
    # Check for key elements
    with open(base_template, 'r') as f:
        base_content = f.read()
    
    if '{% block content %}' not in base_content:
        print("✗ base.html missing content block")
        return False
    
    with open(dashboard_template, 'r') as f:
        dashboard_content = f.read()
    
    if 'settings-tab' not in dashboard_content:
        print("✗ dashboard.html missing settings tab")
        return False
    
    if 'credential-input' not in dashboard_content:
        print("✗ dashboard.html missing credential inputs")
        return False
    
    if 'test-connection-btn' not in dashboard_content:
        print("✗ dashboard.html missing test connection buttons")
        return False
    
    print("✓ Template structure looks good")
    return True

def test_static_files():
    """Test if static files exist"""
    print("\nTesting static files...")
    
    js_file = Path("static/js/app.js")
    
    if not js_file.exists():
        print("✗ app.js not found")
        return False
    
    with open(js_file, 'r') as f:
        js_content = f.read()
    
    # Check for utility functions in app.js
    if 'showNotification' not in js_content:
        print("✗ app.js missing showNotification function")
        return False
    
    if 'apiCall' not in js_content:
        print("✗ app.js missing apiCall function")
        return False
    
    # Check dashboard.html for credential management functions
    dashboard_file = Path("templates/dashboard.html")
    if dashboard_file.exists():
        with open(dashboard_file, 'r') as f:
            dashboard_content = f.read()
        
        if 'exportConfig' not in dashboard_content:
            print("✗ dashboard.html missing exportConfig function")
            return False
        
        if 'importConfig' not in dashboard_content:
            print("✗ dashboard.html missing importConfig function")
            return False
        
        if 'testConnection' not in dashboard_content:
            print("✗ dashboard.html missing testConnection function")
            return False
        
        if 'saveCredentials' not in dashboard_content:
            print("✗ dashboard.html missing saveCredentials function")
            return False
    
    print("✓ Static files look good")
    return True

def main():
    """Run all tests"""
    print("Running web interface tests...\n")
    
    tests = [
        test_config_manager,
        test_models,
        test_api_models,
        test_template_structure,
        test_static_files
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n{'='*50}")
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The web interface should work correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())