#!/usr/bin/env python3
"""
TerraRisk AI - SMTP Live Connection Tester
Usage: python test_smtp.py [recipient_email]
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()

from mailer import send_verification_email, is_smtp_configured, get_smtp_config

def main():
    recipient = sys.argv[1] if len(sys.argv) > 1 else os.getenv("SMTP_USER", "")
    host, port, user, password, from_addr, use_tls = get_smtp_config()

    print("=" * 65)
    print("TERRARISK AI - SMTP DISPATCH CONFIGURATION CHECK")
    print("=" * 65)
    print(f"  SMTP Host:     {host or '[NOT SET]'}")
    print(f"  SMTP Port:     {port}")
    print(f"  SMTP User:     {user or '[NOT SET]'}")
    print(f"  SMTP Password: {'*' * len(password) if password else '[NOT SET]'}")
    print(f"  SMTP From:     {from_addr}")
    print(f"  Use TLS:       {use_tls}")
    print("=" * 65)

    if not is_smtp_configured():
        print("\n[!] SMTP is NOT fully configured in backend/.env.")
        print("    Add the following lines to your backend/.env file:")
        print("    SMTP_HOST=smtp.gmail.com")
        print("    SMTP_PORT=587")
        print("    SMTP_USER=your-email@gmail.com")
        print("    SMTP_PASSWORD=your-16-char-app-password")
        print("    SMTP_FROM=TerraRisk AI <your-email@gmail.com>")
        print("    SMTP_USE_TLS=true")
        print("\n    Currently running in Development Fallback Mode (prints to console).")
        return

    if not recipient:
        print("\n[!] Please provide a test recipient email:")
        print("    python test_smtp.py your-email@domain.com")
        return

    print(f"\n[>] Attempting live dispatch to: {recipient} ...")
    test_otp = "849201"
    success, msg = send_verification_email(recipient, "Test Explorer", test_otp)
    if success:
        print(f"\n[OK] SUCCESS! Live email delivered to {recipient}.")
        print("     Check your inbox (and spam/promotions folder) for the 6-digit code.")
    else:
        print(f"\n[FAIL] Dispatch failed: {msg}")

if __name__ == "__main__":
    main()
