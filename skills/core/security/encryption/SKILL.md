---
name: encryption
description: Data encryption and cryptographic operations
version: 1.0.0
category: security
technologies: [python, cryptography, aes, rsa, hashing]
triggers:
  - encryption
  - cryptography
  - hashing
  - secrets
  - data protection
---

# Encryption & Cryptography

Data encryption, hashing, and cryptographic operations.

## Symmetric Encryption (AES)

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import base64

class SymmetricEncryption:
    """Simple symmetric encryption using Fernet (AES-128-CBC)."""

    @staticmethod
    def generate_key() -> bytes:
        return Fernet.generate_key()

    @staticmethod
    def encrypt(data: bytes, key: bytes) -> bytes:
        f = Fernet(key)
        return f.encrypt(data)

    @staticmethod
    def decrypt(encrypted_data: bytes, key: bytes) -> bytes:
        f = Fernet(key)
        return f.decrypt(encrypted_data)

class AESEncryption:
    """AES-256-GCM encryption for more control."""

    @staticmethod
    def generate_key() -> bytes:
        return os.urandom(32)  # 256 bits

    @staticmethod
    def encrypt(plaintext: bytes, key: bytes) -> dict:
        nonce = os.urandom(12)
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()

        return {
            'ciphertext': base64.b64encode(ciphertext).decode(),
            'nonce': base64.b64encode(nonce).decode(),
            'tag': base64.b64encode(encryptor.tag).decode()
        }

    @staticmethod
    def decrypt(encrypted: dict, key: bytes) -> bytes:
        ciphertext = base64.b64decode(encrypted['ciphertext'])
        nonce = base64.b64decode(encrypted['nonce'])
        tag = base64.b64decode(encrypted['tag'])

        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()
```

## Asymmetric Encryption (RSA)

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

class RSAEncryption:
    @staticmethod
    def generate_key_pair(key_size: int = 2048):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        public_key = private_key.public_key()

        return private_key, public_key

    @staticmethod
    def serialize_private_key(private_key, password: bytes = None) -> bytes:
        encryption = (
            serialization.BestAvailableEncryption(password)
            if password else serialization.NoEncryption()
        )
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption
        )

    @staticmethod
    def serialize_public_key(public_key) -> bytes:
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    @staticmethod
    def encrypt(plaintext: bytes, public_key) -> bytes:
        return public_key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    @staticmethod
    def decrypt(ciphertext: bytes, private_key) -> bytes:
        return private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    @staticmethod
    def sign(message: bytes, private_key) -> bytes:
        return private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

    @staticmethod
    def verify(message: bytes, signature: bytes, public_key) -> bool:
        try:
            public_key.verify(
                signature,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except:
            return False
```

## Hashing

```python
import hashlib
import hmac
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

class Hashing:
    @staticmethod
    def sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def sha512(data: bytes) -> str:
        return hashlib.sha512(data).hexdigest()

    @staticmethod
    def hmac_sha256(data: bytes, key: bytes) -> str:
        return hmac.new(key, data, hashlib.sha256).hexdigest()

    @staticmethod
    def verify_hmac(data: bytes, signature: str, key: bytes) -> bool:
        expected = hmac.new(key, data, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

class KeyDerivation:
    @staticmethod
    def derive_key(password: str, salt: bytes = None, length: int = 32) -> tuple:
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            iterations=480000,  # OWASP recommended
            backend=default_backend()
        )

        key = kdf.derive(password.encode())
        return key, salt
```

## Field-Level Encryption

```python
class FieldEncryptor:
    """Encrypt specific fields in data structures."""

    def __init__(self, key: bytes):
        self.fernet = Fernet(key)

    def encrypt_field(self, value: str) -> str:
        encrypted = self.fernet.encrypt(value.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_field(self, encrypted_value: str) -> str:
        encrypted = base64.b64decode(encrypted_value)
        return self.fernet.decrypt(encrypted).decode()

    def encrypt_dict(self, data: dict, fields: list) -> dict:
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                result[field] = self.encrypt_field(str(result[field]))
        return result

    def decrypt_dict(self, data: dict, fields: list) -> dict:
        result = data.copy()
        for field in fields:
            if field in result and result[field]:
                result[field] = self.decrypt_field(result[field])
        return result

# Usage
encryptor = FieldEncryptor(key)
user_data = {
    "id": 1,
    "email": "user@example.com",
    "ssn": "123-45-6789",
    "credit_card": "4111111111111111"
}

# Encrypt sensitive fields
encrypted = encryptor.encrypt_dict(user_data, ["ssn", "credit_card"])
```

## Envelope Encryption

```python
class EnvelopeEncryption:
    """
    Envelope encryption: encrypt data with a DEK,
    then encrypt DEK with a KEK.
    """

    def __init__(self, kek: bytes):
        self.kek = kek
        self.kek_fernet = Fernet(kek)

    def encrypt(self, data: bytes) -> dict:
        # Generate Data Encryption Key
        dek = Fernet.generate_key()
        data_fernet = Fernet(dek)

        # Encrypt data with DEK
        encrypted_data = data_fernet.encrypt(data)

        # Encrypt DEK with KEK
        encrypted_dek = self.kek_fernet.encrypt(dek)

        return {
            'encrypted_data': base64.b64encode(encrypted_data).decode(),
            'encrypted_dek': base64.b64encode(encrypted_dek).decode()
        }

    def decrypt(self, envelope: dict) -> bytes:
        encrypted_data = base64.b64decode(envelope['encrypted_data'])
        encrypted_dek = base64.b64decode(envelope['encrypted_dek'])

        # Decrypt DEK with KEK
        dek = self.kek_fernet.decrypt(encrypted_dek)

        # Decrypt data with DEK
        data_fernet = Fernet(dek)
        return data_fernet.decrypt(encrypted_data)
```

## Secrets Management

```python
import keyring
from cryptography.fernet import Fernet

class SecretsManager:
    """Local secrets management using system keyring."""

    SERVICE_NAME = "myapp"

    @classmethod
    def store_secret(cls, name: str, value: str):
        keyring.set_password(cls.SERVICE_NAME, name, value)

    @classmethod
    def get_secret(cls, name: str) -> str:
        return keyring.get_password(cls.SERVICE_NAME, name)

    @classmethod
    def delete_secret(cls, name: str):
        keyring.delete_password(cls.SERVICE_NAME, name)

# For cloud: use AWS Secrets Manager, Azure Key Vault, etc.
```

## Best Practices

1. Never store encryption keys in code
2. Use authenticated encryption (GCM mode)
3. Generate random IVs/nonces for each encryption
4. Use key derivation for password-based encryption
5. Implement key rotation
6. Use envelope encryption for large data
7. Secure key storage (HSM, KMS)
8. Use constant-time comparison for signatures
