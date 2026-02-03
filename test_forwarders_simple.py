#!/usr/bin/env python3
"""
Simple test script for forwarder database functions (without importing auth.py)
"""
import json
import os
from filelock import SoftFileLock

# Forwarders database file
FORWARDERS_DB_FILE = 'forwarders_db.json'
FORWARDERS_DB_LOCK_FILE = 'forwarders_db.json.lock'

def load_forwarders_db():
    """Load forwarders database from file with file locking for thread safety"""
    lock = SoftFileLock(FORWARDERS_DB_LOCK_FILE, timeout=10)
    with lock:
        if os.path.exists(FORWARDERS_DB_FILE):
            try:
                with open(FORWARDERS_DB_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {'b3': [], 'pp': []}
        return {'b3': [], 'pp': []}

def save_forwarders_db(db):
    """Save forwarders database to file with file locking for thread safety"""
    lock = SoftFileLock(FORWARDERS_DB_LOCK_FILE, timeout=10)
    with lock:
        with open(FORWARDERS_DB_FILE, 'w') as f:
            json.dump(db, f, indent=2)

def add_forwarder(gateway, name, bot_token, chat_id):
    """Add a new forwarder"""
    db = load_forwarders_db()
    forwarder = {
        'name': name,
        'bot_token': bot_token,
        'chat_id': chat_id,
        'enabled': True
    }
    db[gateway].append(forwarder)
    save_forwarders_db(db)
    return True

def remove_forwarder(gateway, index):
    """Remove a forwarder by index"""
    db = load_forwarders_db()
    if 0 <= index < len(db[gateway]):
        db[gateway].pop(index)
        save_forwarders_db(db)
        return True
    return False

def update_forwarder(gateway, index, name=None, bot_token=None, chat_id=None, enabled=None):
    """Update a forwarder"""
    db = load_forwarders_db()
    if 0 <= index < len(db[gateway]):
        if name is not None:
            db[gateway][index]['name'] = name
        if bot_token is not None:
            db[gateway][index]['bot_token'] = bot_token
        if chat_id is not None:
            db[gateway][index]['chat_id'] = chat_id
        if enabled is not None:
            db[gateway][index]['enabled'] = enabled
        save_forwarders_db(db)
        return True
    return False

def get_forwarders(gateway):
    """Get all forwarders for a gateway"""
    db = load_forwarders_db()
    return db.get(gateway, [])

# Test forwarder database functions
def test_forwarders():
    print("🧪 Testing Forwarder Functionality\n")
    
    # Clean up any existing test database
    if os.path.exists(FORWARDERS_DB_FILE):
        os.remove(FORWARDERS_DB_FILE)
    if os.path.exists(FORWARDERS_DB_LOCK_FILE):
        os.remove(FORWARDERS_DB_LOCK_FILE)
    
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
    with open(FORWARDERS_DB_FILE, 'r') as f:
        file_content = json.load(f)
    print(f"   Database content:\n{json.dumps(file_content, indent=2)}")
    print("   ✅ Pass\n")
    
    # Clean up
    if os.path.exists(FORWARDERS_DB_FILE):
        os.remove(FORWARDERS_DB_FILE)
    if os.path.exists(FORWARDERS_DB_LOCK_FILE):
        os.remove(FORWARDERS_DB_LOCK_FILE)
    
    print("✅ All tests passed!")

if __name__ == '__main__':
    test_forwarders()
