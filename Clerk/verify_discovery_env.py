#!/usr/bin/env python
"""
Verify Discovery Processing Environment Variables

This script checks that all required environment variables for discovery processing
are properly set and have the expected values.
"""

import os
import sys
from datetime import datetime

def check_env_var(var_name, expected_value=None, is_required=True, is_secret=False):
    """Check if an environment variable is set and has expected value"""
    value = os.getenv(var_name)
    
    if value is None:
        if is_required:
            print(f"❌ {var_name}: NOT SET (Required)")
            return False
        else:
            print(f"⚠️  {var_name}: NOT SET (Optional)")
            return True
    
    if is_secret:
        # Don't print secret values
        print(f"✅ {var_name}: SET (length: {len(value)})")
    elif expected_value is not None:
        if value == expected_value:
            print(f"✅ {var_name}: {value}")
        else:
            print(f"⚠️  {var_name}: {value} (Expected: {expected_value})")
            return False
    else:
        print(f"✅ {var_name}: {value}")
    
    return True

def main():
    """Main function to check all discovery-related environment variables"""
    print("Discovery Processing Environment Check")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"Container Hostname: {os.uname().nodename}")
    print("=" * 60)
    
    all_good = True
    
    # Discovery-specific variables
    print("\n📋 Discovery Processing Configuration:")
    print("-" * 40)
    all_good &= check_env_var("DISCOVERY_BOUNDARY_MODEL", "gpt-4.1-mini")
    all_good &= check_env_var("DISCOVERY_WINDOW_SIZE", "5")
    all_good &= check_env_var("DISCOVERY_WINDOW_OVERLAP", "1")
    all_good &= check_env_var("DISCOVERY_CONFIDENCE_THRESHOLD", "0.7")
    all_good &= check_env_var("DISCOVERY_CLASSIFICATION_MODEL", "gpt-4.1-mini", is_required=False)
    
    # OpenAI Configuration
    print("\n🤖 OpenAI Configuration:")
    print("-" * 40)
    all_good &= check_env_var("OPENAI_API_KEY", is_secret=True)
    all_good &= check_env_var("CONTEXT_LLM_MODEL", is_required=False)
    
    # Box API Configuration (for discovery file access)
    print("\n📦 Box API Configuration:")
    print("-" * 40)
    all_good &= check_env_var("BOX_CLIENT_ID", is_secret=True)
    all_good &= check_env_var("BOX_CLIENT_SECRET", is_secret=True)
    all_good &= check_env_var("BOX_ENTERPRISE_ID", is_secret=True)
    all_good &= check_env_var("BOX_JWT_KEY_ID", is_secret=True)
    all_good &= check_env_var("BOX_PRIVATE_KEY", is_secret=True)
    all_good &= check_env_var("BOX_PASSPHRASE", is_secret=True)
    
    # Qdrant Configuration (for vector storage)
    print("\n🗄️  Qdrant Configuration:")
    print("-" * 40)
    all_good &= check_env_var("QDRANT_HOST")
    all_good &= check_env_var("QDRANT_PORT", "6333")
    all_good &= check_env_var("QDRANT_API_KEY", is_secret=True)
    all_good &= check_env_var("QDRANT_HTTPS", "true")
    
    # Optional Processing Configuration
    print("\n⚙️  Optional Processing Configuration:")
    print("-" * 40)
    check_env_var("CHUNK_SIZE", "1400", is_required=False)
    check_env_var("CHUNK_OVERLAP", "200", is_required=False)
    check_env_var("MVP_MODE", "false", is_required=False)
    
    # Case Management Configuration
    print("\n📁 Case Management Configuration:")
    print("-" * 40)
    check_env_var("ENABLE_CASE_ISOLATION", "true", is_required=False)
    check_env_var("MAX_CASE_NAME_LENGTH", "50", is_required=False)
    
    # Check settings file
    print("\n📄 Settings File Check:")
    print("-" * 40)
    settings_path = "/app/config/settings.py"
    if os.path.exists(settings_path):
        print(f"✅ Settings file exists: {settings_path}")
        # Check if it imports discovery settings
        try:
            with open(settings_path, 'r') as f:
                content = f.read()
                if 'discovery' in content:
                    print("✅ Discovery settings found in settings.py")
                else:
                    print("⚠️  Discovery settings not found in settings.py")
        except Exception as e:
            print(f"⚠️  Could not read settings file: {e}")
    else:
        print(f"❌ Settings file not found: {settings_path}")
        all_good = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_good:
        print("✅ All required environment variables are properly set!")
        print("\nYou can now run discovery processing.")
    else:
        print("❌ Some required environment variables are missing or incorrect!")
        print("\nPlease set the missing variables in your .env file or environment.")
        print("\nExample .env entries:")
        print("DISCOVERY_BOUNDARY_MODEL=gpt-4.1-mini")
        print("DISCOVERY_WINDOW_SIZE=5")
        print("DISCOVERY_WINDOW_OVERLAP=1")
        print("DISCOVERY_CONFIDENCE_THRESHOLD=0.7")
    
    # Test OpenAI connection if API key is set
    if os.getenv("OPENAI_API_KEY"):
        print("\n🔍 Testing OpenAI Connection...")
        print("-" * 40)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            # Try to list models
            models = client.models.list()
            # Check if our model is available
            model_names = [m.id for m in models.data]
            if "gpt-4.1-mini" in model_names or any("gpt-4" in m for m in model_names):
                print("✅ OpenAI connection successful")
                print("✅ GPT-4 models available")
            else:
                print("⚠️  OpenAI connection successful but gpt-4.1-mini not in model list")
                print(f"   Available GPT models: {[m for m in model_names if 'gpt' in m][:5]}")
        except Exception as e:
            print(f"❌ OpenAI connection failed: {e}")
            all_good = False
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())