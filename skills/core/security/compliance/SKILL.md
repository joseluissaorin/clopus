---
name: compliance
description: Security compliance and regulatory requirements
version: 1.0.0
category: security
technologies: [gdpr, hipaa, pci-dss, soc2]
triggers:
  - compliance
  - gdpr
  - hipaa
  - pci-dss
  - soc2
  - data privacy
---

# Security Compliance

Implementing security compliance for regulatory requirements.

## GDPR Compliance

### Data Subject Rights

```python
from datetime import datetime
from typing import Optional
import json

class GDPRCompliance:
    """GDPR data subject rights implementation."""

    async def export_user_data(self, user_id: str) -> dict:
        """Right to data portability - export all user data."""
        data = {
            "export_date": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "data": {}
        }

        # Collect from all data sources
        data["data"]["profile"] = await self.get_profile(user_id)
        data["data"]["orders"] = await self.get_orders(user_id)
        data["data"]["preferences"] = await self.get_preferences(user_id)
        data["data"]["activity_log"] = await self.get_activity(user_id)

        return data

    async def delete_user_data(self, user_id: str) -> dict:
        """Right to erasure - delete all user data."""
        deleted = {
            "user_id": user_id,
            "deleted_at": datetime.utcnow().isoformat(),
            "sources": []
        }

        # Delete from all sources
        await self.delete_profile(user_id)
        deleted["sources"].append("profile")

        await self.delete_orders(user_id)
        deleted["sources"].append("orders")

        await self.anonymize_logs(user_id)
        deleted["sources"].append("logs_anonymized")

        return deleted

    async def update_consent(self, user_id: str, consents: dict) -> dict:
        """Manage user consent preferences."""
        consent_record = {
            "user_id": user_id,
            "updated_at": datetime.utcnow().isoformat(),
            "consents": consents,
            "ip_address": self.get_client_ip(),
            "user_agent": self.get_user_agent()
        }

        await self.store_consent(consent_record)
        return consent_record
```

### Privacy Policy Enforcement

```python
class DataProcessingAgreement:
    """Track data processing activities."""

    def __init__(self):
        self.processing_activities = []

    def register_activity(
        self,
        purpose: str,
        data_categories: list,
        recipients: list,
        retention_period: str,
        legal_basis: str
    ):
        activity = {
            "purpose": purpose,
            "data_categories": data_categories,
            "recipients": recipients,
            "retention_period": retention_period,
            "legal_basis": legal_basis,  # consent, contract, legal_obligation, etc.
            "registered_at": datetime.utcnow().isoformat()
        }
        self.processing_activities.append(activity)

    def generate_ropa(self) -> dict:
        """Generate Record of Processing Activities."""
        return {
            "organization": "Company Name",
            "dpo_contact": "dpo@company.com",
            "activities": self.processing_activities,
            "generated_at": datetime.utcnow().isoformat()
        }
```

## PCI-DSS Compliance

### Card Data Handling

```python
import re
from cryptography.fernet import Fernet

class PCICompliance:
    """PCI-DSS compliant card data handling."""

    def __init__(self, encryption_key: bytes):
        self.fernet = Fernet(encryption_key)

    def mask_card_number(self, card_number: str) -> str:
        """Mask all but last 4 digits."""
        clean = re.sub(r'\D', '', card_number)
        return f"****-****-****-{clean[-4:]}"

    def tokenize_card(self, card_data: dict) -> str:
        """Replace card data with a token."""
        import uuid
        token = str(uuid.uuid4())

        # Store encrypted card data with token reference
        # In production, use a PCI-compliant vault
        encrypted = self.fernet.encrypt(json.dumps(card_data).encode())
        self.store_tokenized_card(token, encrypted)

        return token

    def validate_card_number(self, card_number: str) -> bool:
        """Luhn algorithm validation."""
        clean = re.sub(r'\D', '', card_number)

        def digits_of(n):
            return [int(d) for d in str(n)]

        digits = digits_of(clean)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]

        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d * 2))

        return checksum % 10 == 0

    def log_access(self, user_id: str, action: str, card_token: str):
        """Log all access to cardholder data."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "card_token": card_token,
            "ip_address": self.get_client_ip()
        }
        self.audit_logger.info(json.dumps(log_entry))
```

## HIPAA Compliance

### PHI Handling

```python
class HIPAACompliance:
    """HIPAA compliant PHI handling."""

    PHI_FIELDS = [
        'name', 'address', 'dates', 'phone', 'fax', 'email',
        'ssn', 'medical_record_number', 'health_plan_id',
        'account_number', 'certificate_number', 'vehicle_id',
        'device_id', 'url', 'ip_address', 'biometric', 'photo'
    ]

    def __init__(self, encryption_key: bytes):
        self.fernet = Fernet(encryption_key)

    def encrypt_phi(self, data: dict) -> dict:
        """Encrypt PHI fields."""
        encrypted = data.copy()
        for field in self.PHI_FIELDS:
            if field in encrypted and encrypted[field]:
                value = json.dumps(encrypted[field])
                encrypted[field] = self.fernet.encrypt(value.encode()).decode()
        return encrypted

    def decrypt_phi(self, data: dict) -> dict:
        """Decrypt PHI fields."""
        decrypted = data.copy()
        for field in self.PHI_FIELDS:
            if field in decrypted and decrypted[field]:
                value = self.fernet.decrypt(decrypted[field].encode())
                decrypted[field] = json.loads(value.decode())
        return decrypted

    def create_audit_log(
        self,
        user_id: str,
        patient_id: str,
        action: str,
        phi_accessed: list
    ):
        """Create HIPAA-compliant audit log entry."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "patient_id": patient_id,
            "action": action,
            "phi_fields_accessed": phi_accessed,
            "workstation": self.get_workstation_id(),
            "ip_address": self.get_client_ip()
        }

    def minimum_necessary(self, data: dict, required_fields: list) -> dict:
        """Return only minimum necessary PHI."""
        return {k: v for k, v in data.items() if k in required_fields}
```

## SOC 2 Controls

```python
class SOC2Controls:
    """SOC 2 Trust Services Criteria implementation."""

    # Security
    async def verify_access_control(self, user_id: str, resource: str) -> bool:
        """CC6.1 - Logical and physical access controls."""
        permissions = await self.get_user_permissions(user_id)
        return resource in permissions

    # Availability
    async def health_check(self) -> dict:
        """CC7.1 - System availability monitoring."""
        return {
            "database": await self.check_database(),
            "cache": await self.check_cache(),
            "external_apis": await self.check_external_apis(),
            "timestamp": datetime.utcnow().isoformat()
        }

    # Processing Integrity
    def validate_input(self, data: dict, schema: dict) -> tuple:
        """CC8.1 - Input validation."""
        from jsonschema import validate, ValidationError
        try:
            validate(data, schema)
            return True, None
        except ValidationError as e:
            return False, str(e)

    # Confidentiality
    def classify_data(self, data: dict) -> str:
        """CC9.1 - Data classification."""
        if any(field in data for field in ['ssn', 'credit_card', 'password']):
            return 'restricted'
        if any(field in data for field in ['email', 'phone', 'address']):
            return 'confidential'
        return 'internal'

    # Privacy
    async def check_consent(self, user_id: str, purpose: str) -> bool:
        """P1.1 - Privacy consent verification."""
        consents = await self.get_user_consents(user_id)
        return consents.get(purpose, False)
```

## Audit Logging

```python
import structlog
from datetime import datetime

class ComplianceAuditLogger:
    def __init__(self):
        self.logger = structlog.get_logger()

    def log_event(
        self,
        event_type: str,
        user_id: str,
        resource: str,
        action: str,
        outcome: str,
        details: dict = None
    ):
        self.logger.info(
            "compliance_audit",
            event_type=event_type,
            user_id=user_id,
            resource=resource,
            action=action,
            outcome=outcome,
            details=details or {},
            timestamp=datetime.utcnow().isoformat(),
            compliance_version="1.0"
        )
```

## Best Practices

1. Implement data classification
2. Encrypt data at rest and in transit
3. Maintain comprehensive audit logs
4. Implement access controls (RBAC)
5. Regular security assessments
6. Incident response procedures
7. Employee security training
8. Vendor risk management
