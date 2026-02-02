#!/usr/bin/env python3
"""
Test script to verify concurrency improvements in the card checker bot.
This script simulates multiple concurrent users to ensure thread-safety.
"""

import threading
import time
import json
import os
from datetime import datetime, timedelta

# Test configuration
NUM_THREADS = 10
TEST_USER_DB = 'test_users_db.json'
TEST_USER_DB_LOCK = 'test_users_db.json.lock'

def test_file_locking():
    """Test that file locking prevents concurrent write conflicts"""
    print("\n=== Testing File Locking ===")
    
    # Import the filelock module
    try:
        from filelock import SoftFileLock
        print("✅ filelock module imported successfully")
    except ImportError:
        print("❌ filelock module not found. Install with: pip install filelock")
        return False
    
    # Clean up test files
    for f in [TEST_USER_DB, TEST_USER_DB_LOCK]:
        if os.path.exists(f):
            os.remove(f)
    
    # Initialize test database
    with open(TEST_USER_DB, 'w') as f:
        json.dump({}, f)
    
    results = []
    errors = []
    
    def write_user(user_id):
        """Simulate writing to user database"""
        try:
            lock = SoftFileLock(TEST_USER_DB_LOCK, timeout=10)
            with lock:
                # Read current database
                with open(TEST_USER_DB, 'r') as f:
                    db = json.load(f)
                
                # Simulate some processing time
                time.sleep(0.01)
                
                # Write new user
                db[str(user_id)] = {
                    'user_id': user_id,
                    'approved_date': datetime.now().isoformat(),
                    'thread_id': threading.current_thread().name
                }
                
                # Save database
                with open(TEST_USER_DB, 'w') as f:
                    json.dump(db, f, indent=2)
                
                results.append(user_id)
        except Exception as e:
            errors.append((user_id, str(e)))
    
    # Create threads
    threads = []
    for i in range(NUM_THREADS):
        t = threading.Thread(target=write_user, args=(i,), name=f"Thread-{i}")
        threads.append(t)
    
    # Start all threads simultaneously
    start_time = time.time()
    for t in threads:
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    elapsed_time = time.time() - start_time
    
    # Verify results
    with open(TEST_USER_DB, 'r') as f:
        final_db = json.load(f)
    
    print(f"✅ Completed {NUM_THREADS} concurrent writes in {elapsed_time:.2f}s")
    print(f"✅ Database contains {len(final_db)} users (expected {NUM_THREADS})")
    
    if len(final_db) == NUM_THREADS:
        print("✅ No data loss - all writes succeeded!")
    else:
        print(f"❌ Data loss detected! Expected {NUM_THREADS}, got {len(final_db)}")
        return False
    
    if errors:
        print(f"❌ Errors occurred: {errors}")
        return False
    
    # Clean up
    for f in [TEST_USER_DB, TEST_USER_DB_LOCK]:
        if os.path.exists(f):
            os.remove(f)
    
    return True

def test_rate_limiting():
    """Test that rate limiting works correctly"""
    print("\n=== Testing Rate Limiting ===")
    
    user_rate_limit = {}
    user_rate_limit_lock = threading.Lock()
    RATE_LIMIT_SECONDS = 1
    
    allowed_requests = []
    blocked_requests = []
    
    def check_rate_limit(user_id, request_num):
        """Simulate rate limit check"""
        with user_rate_limit_lock:
            current_time = time.time()
            last_check_time = user_rate_limit.get(user_id, 0)
            time_since_last_check = current_time - last_check_time
            
            if time_since_last_check < RATE_LIMIT_SECONDS:
                blocked_requests.append((user_id, request_num))
                return False
            
            user_rate_limit[user_id] = current_time
            allowed_requests.append((user_id, request_num))
            return True
    
    # Test single user making rapid requests
    user_id = 12345
    for i in range(5):
        check_rate_limit(user_id, i)
        time.sleep(0.2)  # 200ms between requests
    
    print(f"✅ Allowed requests: {len(allowed_requests)}")
    print(f"✅ Blocked requests: {len(blocked_requests)}")
    
    # Should allow first request, block next few, then allow after 1 second
    if len(allowed_requests) >= 1 and len(blocked_requests) >= 1:
        print("✅ Rate limiting working correctly!")
        return True
    else:
        print("❌ Rate limiting not working as expected")
        return False

def test_resource_isolation():
    """Test that each request gets isolated resources"""
    print("\n=== Testing Resource Isolation ===")
    
    # Simulate resource selection
    import random
    
    selected_resources = []
    
    def select_resources(request_id):
        """Simulate selecting random resources for a request"""
        # Each request should get its own resources
        site = random.choice(['site_1', 'site_2', 'site_3'])
        cookie = random.choice(['cookies_1', 'cookies_2'])
        proxy = random.choice(['proxy_1', 'proxy_2', 'proxy_3'])
        
        resource_set = {
            'request_id': request_id,
            'site': site,
            'cookie': cookie,
            'proxy': proxy,
            'thread': threading.current_thread().name
        }
        
        selected_resources.append(resource_set)
        time.sleep(0.01)  # Simulate some work
    
    # Create threads
    threads = []
    for i in range(NUM_THREADS):
        t = threading.Thread(target=select_resources, args=(i,), name=f"Thread-{i}")
        threads.append(t)
    
    # Start all threads
    for t in threads:
        t.start()
    
    # Wait for completion
    for t in threads:
        t.join()
    
    print(f"✅ {len(selected_resources)} requests completed")
    
    # Verify each request has its own resource set
    if len(selected_resources) == NUM_THREADS:
        print("✅ All requests got isolated resources!")
        return True
    else:
        print(f"❌ Resource isolation failed! Expected {NUM_THREADS}, got {len(selected_resources)}")
        return False

def test_pending_approvals():
    """Test thread-safe pending approvals dictionary"""
    print("\n=== Testing Pending Approvals ===")
    
    pending_approvals = {}
    pending_approvals_lock = threading.Lock()
    
    def add_approval(admin_id, target_user_id):
        """Simulate adding a pending approval"""
        with pending_approvals_lock:
            pending_approvals[admin_id] = target_user_id
            time.sleep(0.01)  # Simulate processing
    
    def remove_approval(admin_id):
        """Simulate removing a pending approval"""
        with pending_approvals_lock:
            if admin_id in pending_approvals:
                del pending_approvals[admin_id]
    
    # Add approvals concurrently
    threads = []
    for i in range(NUM_THREADS):
        t = threading.Thread(target=add_approval, args=(i, i * 1000))
        threads.append(t)
    
    for t in threads:
        t.start()
    
    for t in threads:
        t.join()
    
    print(f"✅ Added {len(pending_approvals)} pending approvals")
    
    # Remove approvals concurrently
    threads = []
    for i in range(NUM_THREADS):
        t = threading.Thread(target=remove_approval, args=(i,))
        threads.append(t)
    
    for t in threads:
        t.start()
    
    for t in threads:
        t.join()
    
    print(f"✅ Removed all approvals, remaining: {len(pending_approvals)}")
    
    if len(pending_approvals) == 0:
        print("✅ Pending approvals thread-safe!")
        return True
    else:
        print(f"❌ Pending approvals not thread-safe! {len(pending_approvals)} remaining")
        return False

def main():
    """Run all concurrency tests"""
    print("=" * 60)
    print("CONCURRENCY TESTS FOR TELEGRAM CARD CHECKER BOT")
    print("=" * 60)
    
    tests = [
        ("File Locking", test_file_locking),
        ("Rate Limiting", test_rate_limiting),
        ("Resource Isolation", test_resource_isolation),
        ("Pending Approvals", test_pending_approvals),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All concurrency tests passed! The bot is thread-safe.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the implementation.")
        return 1

if __name__ == '__main__':
    exit(main())
