#!/usr/bin/env python
"""
Setup script to configure ALLOWED_HOSTS for Render deployment
"""
import os
import sys

def generate_render_config():
    """Generate environment variables for Render"""
    print("=== RENDER ENVIRONMENT VARIABLES SETUP ===")
    print("\nIn your Render dashboard, set these Environment Variables:")
    print("\n1. BASIC SETTINGS:")
    print("   DEBUG=False")
    print("   ALLOWED_HOSTS=your-app-name.onrender.com,www.your-app-name.onrender.com")
    
    print("\n2. SECURITY SETTINGS:")
    print("   SECRET_KEY=django-insecure-$(openssl rand -base64 50)")
    print("   # Or generate a new key: https://djecrety.ir/")
    
    print("\n3. EXAMPLE:")
    print("   If your app is 'dailyfish' on Render:")
    print("   ALLOWED_HOSTS=dailyfish.onrender.com,www.dailyfish.onrender.com")
    
    print("\n4. ALTERNATIVE - Use wildcard (less secure but convenient):")
    print("   ALLOWED_HOSTS=.onrender.com")
    
    print("\n=== STEPS TO CONFIGURE ===")
    print("1. Go to your Render Web Service")
    print("2. Click on 'Environment' tab")
    print("3. Add the environment variables above")
    print("4. Click 'Save Changes'")
    print("5. Wait for automatic redeploy")
    
    print("\n=== VERIFICATION ===")
    print("After deployment, test:")
    print("https://your-app-name.onrender.com/admin/")
    print("Username: admin")
    print("Password: admin")

if __name__ == '__main__':
    generate_render_config()
