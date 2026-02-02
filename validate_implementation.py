#!/usr/bin/env python3
"""
Simple validation script for async PPCP checker
This script validates the code structure without running actual tests
"""
import os
import sys

def validate_files():
    """Validate that all required files exist"""
    required_files = [
        'ppcp/async_ppcpgatewaycvv.py',
        'ppcp/rate_limiter.py',
        'ppcp/metrics.py',
        'run_production.py',
        '.env.example'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"Missing files: {missing_files}")
        return False
    
    print("All required files exist!")
    return True

def validate_syntax():
    """Validate Python syntax"""
    files_to_check = [
        'ppcp/async_ppcpgatewaycvv.py',
        'ppcp/rate_limiter.py',
        'ppcp/metrics.py',
        'run_production.py',
        'test_async_ppcp.py'
    ]
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    compile(f.read(), file_path, 'exec')
                print(f"✓ Syntax OK: {file_path}")
            except SyntaxError as e:
                print(f"✗ Syntax Error in {file_path}: {e}")
                return False
            except Exception as e:
                print(f"✗ Error checking {file_path}: {e}")
                return False
    
    return True

def main():
    """Main validation function"""
    print("Validating PPCP checker implementation...")
    
    if not validate_files():
        return False
    
    if not validate_syntax():
        return False
    
    print("\n✅ All validations passed!")
    print("\nTo use the optimized PPCP checker in production:")
    print("1. Install required dependencies: pip install -r requirements.txt")
    print("2. Copy .env.example to .env and configure your settings")
    print("3. Run: python run_production.py")
    print("4. For single card checking: import ppcp.async_ppcpgatewaycvv and use check_single_card()")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)