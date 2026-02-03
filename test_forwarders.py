#!/usr/bin/env python3
"""
Test script for forwarder functionality
"""
import json
import os

# Test forwarder database functions
def test_forwarders():
    print("🧪 Testing Forwarder Functionality\n")
    
    # Import the functions from auth.py
    import sys
    sys.path.insert(0, '/vercel/sandbox')
    from auth import (
        load_forwarders_db, 
        save_forwarders_db, 
        add_forwarder, 
        remove_forwarder, 
        update_forwarder, 
        get_forwarders
    )
    
    # Clean up any existing test database
    if os.path.exists('forwarders_db.json'):
        os.remove('forwarders_db.json')
    
    print("1. Testing load_forwarders_db (should create empty structure)...")
    db = load_forwarders_db()
    assert db == {'b3': [], 'pp': []}, f"Expected empty db, got {db}"
    print("   ✅ Pass\n")
    
    print("2. Testing add_forwarder for B3...")
    add_forwarder('b3', 'Test B3 Channel', '1234567890:ABCdefGHI', '-1001234567890')
    forwarders = get_forwarders('b3')
    assert len(forwarders) == 1, f"Expected 1 forwarder, got {len(forwarders)}"
    assert forwarders[0]['name'] == 'Test B3 Channel'
    assert forwarders[0]['bot_token'] == '1234567890:ABCdefGHI'
    assert forwarders[0]['chat_id'] == '-1001234567890'
    assert forwarders[0]['enabled'] == True
    print("   ✅ Pass\n")
    
    print("3. Testing add_forwarder for PP...")
    add_forwarder('pp', 'Test PP Channel', '9876543210:XYZabcDEF', '-1009876543210')
    forwarders = get_forwarders('pp')
    assert len(forwarders) == 1, f"Expected 1 forwarder, got {len(forwarders)}"
    assert forwarders[0]['name'] == 'Test PP Channel'
    print("   ✅ Pass\n")
    
    print("4. Testing add multiple forwarders...")
    add_forwarder('b3', 'Second B3 Channel', '1111111111:AAAAA', '-1001111111111')
    forwarders = get_forwarders('b3')
    assert len(forwarders) == 2, f"Expected 2 forwarders, got {len(forwarders)}"
    print("   ✅ Pass\n")
    
    print("5. Testing update_forwarder (name)...")
    update_forwarder('b3', 0, name='Updated B3 Channel')
    forwarders = get_forwarders('b3')
    assert forwarders[0]['name'] == 'Updated B3 Channel'
    print("   ✅ Pass\n")
    
    print("6. Testing update_forwarder (enabled)...")
    update_forwarder('b3', 0, enabled=False)
    forwarders = get_forwarders('b3')
    assert forwarders[0]['enabled'] == False
    print("   ✅ Pass\n")
    
    print("7. Testing update_forwarder (bot_token and chat_id)...")
    update_forwarder('b3', 0, bot_token='NEW_TOKEN', chat_id='NEW_CHAT_ID')
    forwarders = get_forwarders('b3')
    assert forwarders[0]['bot_token'] == 'NEW_TOKEN'
    assert forwarders[0]['chat_id'] == 'NEW_CHAT_ID'
    print("   ✅ Pass\n")
    
    print("8. Testing remove_forwarder...")
    result = remove_forwarder('b3', 1)
    assert result == True
    forwarders = get_forwarders('b3')
    assert len(forwarders) == 1, f"Expected 1 forwarder after removal, got {len(forwarders)}"
    print("   ✅ Pass\n")
    
    print("9. Testing remove_forwarder with invalid index...")
    result = remove_forwarder('b3', 999)
    assert result == False
    print("   ✅ Pass\n")
    
    print("10. Testing persistence (reload from file)...")
    db = load_forwarders_db()
    assert len(db['b3']) == 1
    assert len(db['pp']) == 1
    assert db['b3'][0]['name'] == 'Updated B3 Channel'
    print("   ✅ Pass\n")
    
    print("11. Checking database file structure...")
    with open('forwarders_db.json', 'r') as f:
        file_content = json.load(f)
    print(f"   Database content:\n{json.dumps(file_content, indent=2)}")
    print("   ✅ Pass\n")
    
    # Clean up
    if os.path.exists('forwarders_db.json'):
        os.remove('forwarders_db.json')
    if os.path.exists('forwarders_db.json.lock'):
        os.remove('forwarders_db.json.lock')
    
    print("✅ All tests passed!")

if __name__ == '__main__':
    test_forwarders()
