"""
Cryptographic utilities for PostgreSQL Backup & Restore Tool
"""

import hashlib
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


def generate_key(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """Generate encryption key from password"""
    if salt is None:
        salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def encrypt_file(file_path: Path, password: str, output_path: Optional[Path] = None) -> Path:
    """Encrypt a file with password"""
    if output_path is None:
        output_path = file_path.with_suffix(file_path.suffix + '.enc')
    
    key, salt = generate_key(password)
    fernet = Fernet(key)
    
    # Read and encrypt file
    with open(file_path, 'rb') as f:
        data = f.read()
    
    encrypted_data = fernet.encrypt(data)
    
    # Write salt + encrypted data
    with open(output_path, 'wb') as f:
        f.write(salt + encrypted_data)
    
    return output_path


def decrypt_file(encrypted_path: Path, password: str, output_path: Optional[Path] = None) -> Path:
    """Decrypt a file with password"""
    if output_path is None:
        # Remove .enc extension
        if encrypted_path.suffix == '.enc':
            output_path = encrypted_path.with_suffix('')
        else:
            output_path = encrypted_path.with_suffix('.dec')
    
    # Read salt + encrypted data
    with open(encrypted_path, 'rb') as f:
        salt = f.read(16)  # First 16 bytes are salt
        encrypted_data = f.read()
    
    # Generate key from password and salt
    key, _ = generate_key(password, salt)
    fernet = Fernet(key)
    
    # Decrypt data
    decrypted_data = fernet.decrypt(encrypted_data)
    
    # Write decrypted data
    with open(output_path, 'wb') as f:
        f.write(decrypted_data)
    
    return output_path


def generate_checksum(file_path: Path, algorithm: str = 'sha256') -> str:
    """Generate file checksum"""
    hash_func = getattr(hashlib, algorithm)()
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def verify_checksum(file_path: Path, expected_checksum: str, algorithm: str = 'sha256') -> bool:
    """Verify file checksum"""
    actual_checksum = generate_checksum(file_path, algorithm)
    return actual_checksum.lower() == expected_checksum.lower()


def generate_encryption_key() -> str:
    """Generate a random encryption key"""
    return Fernet.generate_key().decode()


def encrypt_data(data: bytes, key: str) -> bytes:
    """Encrypt data with key"""
    fernet = Fernet(key.encode())
    return fernet.encrypt(data)


def decrypt_data(encrypted_data: bytes, key: str) -> bytes:
    """Decrypt data with key"""
    fernet = Fernet(key.encode())
    return fernet.decrypt(encrypted_data)