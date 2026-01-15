
import hashlib
from .database import DB

class LoginManager:
    def __init__(self):
        self.db = DB()

    def _hash(self, password):
        """Return SHA256 hash of the password."""
        return hashlib.sha256(password.encode()).hexdigest()

    def login(self, username, password):
        """
        Verify credentials. 
        Supports auto-migration from plain-text to hashed passwords.
        Returns role (str) if successful, None otherwise.
        """
        user = self.db.fetch_one("SELECT id, password, role FROM users WHERE LOWER(username)=?", (username.lower(),))
        if not user:
            return None
        
        user_id, stored_password, role = user
        
        # 1. Check if it matches hashed version (Secure)
        if stored_password == self._hash(password):
            return role
            
        # 2. Check if it matches plain text (Legacy support / Auto-migration)
        if stored_password == password:
            # Migrate to hash immediately
            new_hash = self._hash(password)
            self.db.execute("UPDATE users SET password=? WHERE id=?", (new_hash, user_id))
            print(f"Security Update: Migrated user '{username}' to hashed password.")
            return role
            
        return None

    def create_user(self, username, password, role="Sales"):
        """Create a new user with hashed password."""
        hashed = self._hash(password)
        try:
            self.db.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hashed, role))
            return True
        except Exception as e:
            print(f"Error creating user: {e}")
            return False

    def change_password(self, user_id, new_password):
        """Update user password (hashed)."""
        hashed = self._hash(new_password)
        self.db.execute("UPDATE users SET password=? WHERE id=?", (hashed, user_id))
        return True
