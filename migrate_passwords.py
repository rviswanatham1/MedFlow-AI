"""
Migration script to create user_passwords.csv for existing users.
This script creates a CSV with random passwords (for existing users) and MD5 hash.
"""
import pandas as pd
import hashlib
import os
import secrets
import string

def md5_hash(text: str) -> str:
    """Generate MD5 hash of a string."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def generate_random_password(length: int = 12) -> str:
    """Generate a secure random password."""
    # Use letters (both cases), digits, and some special characters
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def migrate_existing_users():
    """Migrate existing users from patient_demographics.csv to user_passwords.csv."""
    
    # Check if patient_demographics.csv exists
    if not os.path.exists("patient_demographics.csv"):
        print("Error: patient_demographics.csv not found!")
        return
    
    # Read existing patients
    df = pd.read_csv("patient_demographics.csv")
    
    # Create password data
    password_data = []
    
    print(f"Generating random passwords for {len(df)} existing users...")
    
    for _, row in df.iterrows():
        patient_id = row["patient_id"]
        
        # Generate random password for existing users
        password_plain = generate_random_password()
        password_md5 = md5_hash(password_plain)
        
        password_data.append({
            "patient_id": patient_id,
            "password_plain": password_plain,  # For existing users only
            "password_md5": password_md5
        })
    
    # Create DataFrame and save
    passwords_df = pd.DataFrame(password_data)
    passwords_df.to_csv("user_passwords.csv", index=False)
    
    print(f"✅ Successfully migrated {len(password_data)} users to user_passwords.csv")
    print(f"   - File saved: user_passwords.csv")
    print(f"   - Columns: patient_id, password_plain, password_md5")
    print(f"\n⚠️  IMPORTANT: Random passwords have been generated for all existing users.")
    print(f"   Passwords are stored in plain text in user_passwords.csv for existing users only.")
    print(f"   You may want to export these passwords for distribution to users.")

if __name__ == "__main__":
    migrate_existing_users()
