import hashlib
import json
import os
from datetime import datetime
from typing import Dict, Tuple, Any, Optional

# CONFIGURATION
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
FREE_DAILY_LIMIT = 5  # Kuota harian untuk user Free

# INTERNAL HELPERS
def _load_db() -> Dict[str, Any]:
    """Load the full user database."""
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def _save_db(data: Dict[str, Any]) -> None:
    """Save the database atomically."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _hash_password(password: str) -> str:
    """Securely hash the password."""
    return hashlib.sha256(password.encode()).hexdigest()

def _get_today_str() -> str:
    """Return current date as YYYY-MM-DD string."""
    return datetime.now().strftime("%Y-%m-%d")

# AUTHENTICATION FUNCTIONS
def register_user(username: str, password: str) -> Tuple[bool, str]:
    """Register a new user with default 'free' tier."""
    users = _load_db()
    
    if not username or not password:
        return False, "Username dan Password wajib diisi."
    
    if username in users:
        return False, "Username sudah digunakan."
    
    # Initialize User Profile
    users[username] = {
        "password": _hash_password(password),
        "tier": "free",          # Default tier
        "quota_usage": 0,        # Usage counter
        "last_reset": _get_today_str()
    }
    _save_db(users)
    return True, "Registrasi berhasil! Silakan login."

def verify_login(username: str, password: str) -> bool:
    """Verify credentials."""
    users = _load_db()
    if username not in users:
        return False
    
    stored_hash = users[username].get("password")
    input_hash = _hash_password(password)
    return stored_hash == input_hash

# QUOTA & TIER MANAGEMENT
def get_user_tier(username: str) -> str:
    """Get user's current tier (free/pro)."""
    users = _load_db()
    return users.get(username, {}).get("tier", "free")

def check_quota_available(username: str) -> Tuple[bool, str]:
    """
    Check if user has quota left for today.
    Auto-resets quota if the day has changed.
    """
    users = _load_db()
    if username not in users:
        return False, "User not found."
    
    user_data = users[username]
    tier = user_data.get("tier", "free")
    
    # PRO users have no limits
    if tier == "pro":
        return True, "Unlimited Access"
    
    # Handle FREE users
    today = _get_today_str()
    last_reset = user_data.get("last_reset", "")
    
    # Reset counter if new day
    if last_reset != today:
        user_data["last_reset"] = today
        user_data["quota_usage"] = 0
        _save_db(users)
        return True, f"Quota Reset. {FREE_DAILY_LIMIT} left."
    
    # Check Limit
    current_usage = user_data.get("quota_usage", 0)
    if current_usage < FREE_DAILY_LIMIT:
        remaining = FREE_DAILY_LIMIT - current_usage
        return True, f"Sisa kuota: {remaining}"
    else:
        return False, "Kuota harian habis. Upgrade ke PRO untuk akses tanpa batas."

def increment_usage(username: str) -> None:
    """Increment the usage counter after a successful API call."""
    users = _load_db()
    if username in users:
        users[username]["quota_usage"] = users[username].get("quota_usage", 0) + 1
        _save_db(users)

def upgrade_to_pro(username: str) -> None:
    """Upgrade user tier to PRO (Demo function)."""
    users = _load_db()
    if username in users:
        users[username]["tier"] = "pro"
        _save_db(users)