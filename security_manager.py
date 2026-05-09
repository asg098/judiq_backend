# pyrefly: ignore [missing-import]
import jwt
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict

logger = logging.getLogger(__name__)

SECRET_KEY = "JUDIQ_ENTERPRISE_SECRET_KEY_PROD" # In real prod, this comes from ENV
ALGORITHM  = "HS256"

class SecurityManager:
    """
    Enterprise Security Manager — Handles JWT governance, session integrity,
    and audit log generation.
    """
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=60)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[Dict]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT Token expired.")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid JWT Token.")
            return None

class AuditLogger:
    """
    Captures every system interaction for institutional accountability.
    """
    @staticmethod
    def log_interaction(user_id: str, case_id: str, action: str, metadata: dict = None):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "case_id": case_id,
            "action": action,
            "metadata": metadata or {}
        }
        # In a real system, this writes to a dedicated Audit table or ELK stack
        logger.info(f"[AUDIT] {log_entry}")
        from database_manager import DatabaseManager
        try:
            # Simple persistence for audit
            DatabaseManager.save_interaction(log_entry)
        except Exception as e:
            logger.error(f"Audit persistence failed: {e}")
