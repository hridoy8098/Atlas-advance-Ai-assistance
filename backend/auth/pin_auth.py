# backend/auth/pin_auth.py — Atlas 6.0 PIN Authentication
import hashlib
import json
from pathlib import Path
import config


class PinAuth:
    """
    Atlas 6.0 PIN Authentication System
    - 6 digit PIN support
    - Secure hashing
    - PIN change capability
    """

    def __init__(self):
        self.pin_file = config.DATA_DIR / "pin_hash.json"
        self.default_pin = config.AUTH_PIN or "123456"
        self.pin_hash = self._load_pin_hash()

    def _load_pin_hash(self) -> str:
        """Load saved PIN hash from file, otherwise use default"""
        if self.pin_file.exists():
            try:
                data = json.loads(self.pin_file.read_text(encoding="utf-8"))
                return data.get("pin_hash", self._hash_pin(self.default_pin))
            except:
                pass
        # Default PIN hash
        return self._hash_pin(self.default_pin)

    def _hash_pin(self, pin: str) -> str:
        """Securely hash the PIN"""
        return hashlib.sha256(str(pin).encode('utf-8')).hexdigest()

    def _save_pin_hash(self):
        """Save PIN hash to file"""
        try:
            self.pin_file.parent.mkdir(parents=True, exist_ok=True)
            data = {"pin_hash": self.pin_hash}
            self.pin_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"Warning: Could not save PIN hash: {e}")

    def verify(self, pin: str):
        """
        Verify entered PIN
        Returns: (success: bool, message: str)
        """
        if not pin or len(str(pin).strip()) != 6:
            return False, "PIN must be 6 digits"

        entered_hash = self._hash_pin(pin)
        
        if entered_hash == self.pin_hash:
            return True, "Authentication successful"
        else:
            return False, "Incorrect PIN"

    def set_pin(self, new_pin: str):
        """
        Change PIN
        Returns: True if successful, False otherwise
        """
        if not new_pin or len(str(new_pin).strip()) != 6:
            return False

        self.pin_hash = self._hash_pin(new_pin)
        self._save_pin_hash()
        print(f"✅ PIN updated successfully")
        return True

    def is_configured(self) -> bool:
        """Check if a custom PIN has been configured (saved to file)"""
        return self.pin_file.exists()

    def reset_to_default(self):
        """Reset PIN to default (123456)"""
        self.pin_hash = self._hash_pin(self.default_pin)
        self._save_pin_hash()
        return True


# ====================== Singleton Instance ======================
pin_auth = PinAuth()


# ====================== For Direct Testing ======================
if __name__ == "__main__":
    print("=== Atlas PIN Auth Test ===")
    print(f"Default PIN: {config.AUTH_PIN or '123456'}")
    
    # Test verify
    success, msg = pin_auth.verify("123456")
    print(f"Test PIN 123456: {msg} ({success})")
    
    # Test change PIN
    if pin_auth.set_pin("987654"):
        print("PIN changed to 987654 successfully")
        success, msg = pin_auth.verify("987654")
        print(f"New PIN test: {msg} ({success})")