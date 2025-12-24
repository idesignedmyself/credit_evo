#!/usr/bin/env python3
"""
Admin User Seed Script
Creates an admin user for the Credit Engine admin panel.

Usage:
    python -m scripts.seed_admin <email> <username> <password>

Example:
    python -m scripts.seed_admin admin@creditengine.com admin securepassword123
"""
import sys
import os
from uuid import uuid4

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.db_models import UserDB
from app.auth import hash_password


def create_admin_user(email: str, username: str, password: str) -> bool:
    """Create an admin user in the database."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Check if email already exists
        existing = db.query(UserDB).filter(
            (UserDB.email == email) | (UserDB.username == username)
        ).first()

        if existing:
            if existing.email == email:
                print(f"Error: Email '{email}' already exists.")
                if existing.role == "admin":
                    print("This user is already an admin.")
                else:
                    # Upgrade existing user to admin
                    existing.role = "admin"
                    db.commit()
                    print(f"Upgraded existing user '{email}' to admin role.")
                    return True
                return False
            else:
                print(f"Error: Username '{username}' already exists.")
                return False

        # Create new admin user
        admin_user = UserDB(
            id=str(uuid4()),
            email=email,
            username=username,
            password_hash=hash_password(password),
            role="admin"
        )

        db.add(admin_user)
        db.commit()

        print(f"Admin user created successfully!")
        print(f"  Email: {email}")
        print(f"  Username: {username}")
        print(f"  Role: admin")
        return True

    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    email = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    # Basic validation
    if len(password) < 8:
        print("Error: Password must be at least 8 characters.")
        sys.exit(1)

    if "@" not in email:
        print("Error: Invalid email format.")
        sys.exit(1)

    success = create_admin_user(email, username, password)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
