"""
Shared utility functions used across the application.
Consolidates duplicated code from auth.py, ppcp, and paypalpro modules.
"""
import re
import random
import time
from typing import Dict, Optional, Tuple, List
from functools import lru_cache
import logging

# Optional import
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

from .config import (
    COUNTRY_EMOJI_MAP, 
    ADDRESS_DATA, 
    FIRST_NAMES, 
    LAST_NAMES, 
    EMAIL_DOMAINS,
    USER_AGENTS,
    get_config
)

logger = logging.getLogger(__name__)


def normalize_card_format(card_input: str) -> Optional[str]:
    """
    Normalize card format to number|mm|yyyy|cvv.
    
    Supports:
    - 5401683112957490|10|2029|741 (pipe-separated)
    - 5401683112957490|10|29|741 (2-digit year)
    - 4284303806640816 0628 116 (space-separated with mmyy)
    
    Args:
        card_input: Raw card input string
        
    Returns:
        Normalized card string or None if invalid
    """
    card_input = card_input.strip()
    
    # Check if already in pipe format
    if '|' in card_input:
        parts = card_input.split('|')
        if len(parts) == 4:
            number, mm, yy, cvv = parts
            # Validate card number (13-19 digits)
            if not number.isdigit() or not (13 <= len(number) <= 19):
                return None
            # Normalize year to 4 digits
            if len(yy) == 2:
                yy = '20' + yy
            # Validate month
            if not mm.isdigit() or not (1 <= int(mm) <= 12):
                return None
            # Validate CVV (3-4 digits)
            if not cvv.isdigit() or not (3 <= len(cvv) <= 4):
                return None
            return f"{number}|{mm.zfill(2)}|{yy}|{cvv}"
        return None
    
    # Handle space-separated format: number mmyy cvv
    parts = card_input.split()
    if len(parts) == 3:
        number, mmyy, cvv = parts
        if len(mmyy) == 4 and mmyy.isdigit():
            mm = mmyy[:2]
            yy = '20' + mmyy[2:]
            if number.isdigit() and (13 <= len(number) <= 19):
                if 1 <= int(mm) <= 12 and cvv.isdigit() and (3 <= len(cvv) <= 4):
                    return f"{number}|{mm}|{yy}|{cvv}"
    
    return None


def country_code_to_emoji(country_code: Optional[str]) -> str:
    """
    Convert country code to emoji flag.
    
    Args:
        country_code: 2-letter ISO country code
        
    Returns:
        Emoji flag or default flag
    """
    if not country_code or len(country_code) != 2:
        return '🏳️'
    return COUNTRY_EMOJI_MAP.get(country_code.upper(), '🏳️')


def get_country_from_domain(hostname: str) -> str:
    """
    Determine country based on site domain TLD.
    
    Args:
        hostname: Website hostname
        
    Returns:
        2-letter country code
    """
    hostname = hostname.lower()
    
    domain_country_map = {
        '.co.uk': 'GB',
        '.au': 'AU',
        '.ca': 'CA',
        '.co.nz': 'NZ',
        '.nz': 'NZ',
        '.jp': 'JP',
        '.ph': 'PH',
        '.my': 'MY',
        '.sg': 'SG',
        '.th': 'TH',
        '.nl': 'NL',
        '.hk': 'HK',
        '.co.za': 'ZA',
        '.de': 'DE',
        '.fr': 'FR',
        '.it': 'IT',
        '.es': 'ES',
    }
    
    for suffix, country in domain_country_map.items():
        if hostname.endswith(suffix):
            return country
    
    return 'US'  # Default to US


def get_random_address(country: str = 'US') -> Dict[str, str]:
    """
    Get a random address for the specified country.
    
    Args:
        country: 2-letter country code
        
    Returns:
        Address dictionary with street, city, zip, state, phone
    """
    addresses = ADDRESS_DATA.get(country, ADDRESS_DATA.get('US', []))
    if not addresses:
        addresses = ADDRESS_DATA['US']
    return random.choice(addresses)


def generate_random_name() -> Tuple[str, str]:
    """
    Generate random first and last name.
    
    Returns:
        Tuple of (first_name, last_name)
    """
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)


def generate_random_email(first_name: str = None, last_name: str = None) -> str:
    """
    Generate a random email address.
    
    Args:
        first_name: Optional first name to use
        last_name: Optional last name to use
        
    Returns:
        Random email address
    """
    if not first_name or not last_name:
        first_name, last_name = generate_random_name()
    
    domain = random.choice(EMAIL_DOMAINS)
    num = random.randint(1, 999)
    
    # Various email formats
    formats = [
        f"{first_name.lower()}.{last_name.lower()}@{domain}",
        f"{first_name.lower()}{last_name.lower()}{num}@{domain}",
        f"{first_name.lower()}_{last_name.lower()}@{domain}",
        f"{first_name[0].lower()}{last_name.lower()}{num}@{domain}",
    ]
    
    return random.choice(formats)


def get_random_user_agent() -> str:
    """Get a random user agent string."""
    return random.choice(USER_AGENTS)


# BIN info cache
_bin_cache: Dict[str, Dict] = {}
_bin_cache_timestamps: Dict[str, float] = {}
BIN_CACHE_TTL = 3600  # 1 hour


def get_bin_info_cached(bin_number: str, user_agent: str = None) -> Dict[str, str]:
    """
    Get BIN information with caching.
    
    Args:
        bin_number: First 6 digits of card number
        user_agent: User agent for request
        
    Returns:
        BIN info dictionary
    """
    global _bin_cache, _bin_cache_timestamps
    
    # Check cache
    if bin_number in _bin_cache:
        if time.time() - _bin_cache_timestamps.get(bin_number, 0) < BIN_CACHE_TTL:
            return _bin_cache[bin_number]
    
    # Fetch from API
    result = _fetch_bin_info(bin_number, user_agent or get_random_user_agent())
    
    # Cache result
    _bin_cache[bin_number] = result
    _bin_cache_timestamps[bin_number] = time.time()
    
    # Limit cache size
    if len(_bin_cache) > 1000:
        # Remove oldest entries
        oldest_bins = sorted(_bin_cache_timestamps.keys(), key=lambda k: _bin_cache_timestamps[k])[:100]
        for bin_num in oldest_bins:
            _bin_cache.pop(bin_num, None)
            _bin_cache_timestamps.pop(bin_num, None)
    
    return result


def _fetch_bin_info(bin_number: str, user_agent: str) -> Dict[str, str]:
    """
    Fetch BIN information from API.
    
    Args:
        bin_number: First 6 digits of card number
        user_agent: User agent for request
        
    Returns:
        BIN info dictionary
    """
    default_result = {
        'brand': 'Unknown',
        'type': 'Unknown',
        'level': 'Unknown',
        'bank': 'Unknown',
        'country': 'Unknown',
        'emoji': '🏳️'
    }
    
    if not REQUESTS_AVAILABLE:
        return default_result
    
    try:
        response = requests.get(
            f'https://bins.antipublic.cc/bins/{bin_number}',
            timeout=5,
            headers={'User-Agent': user_agent},
            verify=False
        )
        
        if response.status_code == 200 and response.text:
            data = response.json()
            
            if data:
                # Normalize card type
                raw_type = (data.get('type') or data.get('card_type') or '').lower().strip()
                if 'debit' in raw_type:
                    card_type = 'DEBIT'
                elif 'credit' in raw_type:
                    card_type = 'CREDIT'
                else:
                    card_type = 'Unknown'
                
                # Normalize brand
                raw_brand = data.get('brand') or data.get('card_brand') or data.get('card') or ''
                brand = _normalize_card_brand(raw_brand)
                
                # Extract country code for emoji
                country_code = None
                if isinstance(data.get('country'), dict):
                    country_code = data.get('country', {}).get('alpha2') or data.get('country', {}).get('code')
                
                # Extract bank
                if isinstance(data.get('bank'), dict):
                    bank = data.get('bank', {}).get('name') or 'Unknown'
                else:
                    bank = data.get('bank') or data.get('issuer') or data.get('bank_name') or 'Unknown'
                
                # Extract country name
                if isinstance(data.get('country'), dict):
                    country = data.get('country', {}).get('name') or 'Unknown'
                else:
                    country = data.get('country') or data.get('country_name') or 'Unknown'
                
                return {
                    'brand': brand,
                    'type': card_type,
                    'level': (data.get('level') or data.get('card_level') or 'Unknown').upper() if data.get('level') or data.get('card_level') else 'Unknown',
                    'bank': bank,
                    'country': country,
                    'emoji': country_code_to_emoji(country_code)
                }
    except Exception as e:
        logger.debug(f"BIN lookup error for {bin_number}: {e}")
    
    return default_result


def _normalize_card_brand(raw_brand: str) -> str:
    """Normalize card brand name."""
    if not raw_brand:
        return 'Unknown'
    
    raw_brand_lower = raw_brand.lower()
    
    if 'visa' in raw_brand_lower:
        return 'VISA'
    elif 'mastercard' in raw_brand_lower or 'master' in raw_brand_lower:
        return 'MASTERCARD'
    elif 'amex' in raw_brand_lower or 'american express' in raw_brand_lower:
        return 'AMEX'
    elif 'discover' in raw_brand_lower:
        return 'DISCOVER'
    elif 'jcb' in raw_brand_lower:
        return 'JCB'
    elif 'diners' in raw_brand_lower:
        return 'DINERS'
    else:
        return raw_brand.upper()


def parse_proxy_string(proxy_string: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Parse proxy string into requests-compatible format.
    
    Supports formats:
    - host:port
    - host:port:username:password
    
    Args:
        proxy_string: Raw proxy string
        
    Returns:
        Proxy dict for requests or None
    """
    if not proxy_string:
        return None
    
    parts = proxy_string.split(':')
    
    if len(parts) == 2:
        host, port = parts
        proxy_url = f'http://{host}:{port}'
    elif len(parts) == 4:
        host, port, username, password = parts
        proxy_url = f'http://{username}:{password}@{host}:{port}'
    else:
        return None
    
    return {
        'http': proxy_url,
        'https': proxy_url
    }


def extract_between(text: str, start: str, end: str) -> Optional[str]:
    """
    Extract text between two delimiters.
    
    Args:
        text: Source text
        start: Start delimiter
        end: End delimiter
        
    Returns:
        Extracted text or None
    """
    try:
        start_idx = text.index(start) + len(start)
        end_idx = text.index(end, start_idx)
        return text[start_idx:end_idx]
    except ValueError:
        return None


def check_card_status(result: str) -> Tuple[str, str, bool]:
    """
    Check card status from result message.
    
    Args:
        result: Result message from gateway
        
    Returns:
        Tuple of (status, reason, is_approved)
    """
    # Approved patterns
    approved_patterns = [
        'Nice! New payment method added',
        'Payment method successfully added.',
        'Insufficient Funds',
        'Gateway Rejected: avs',
        'Duplicate',
        'Payment method added successfully',
        'Invalid postal code or street address',
    ]
    
    # CVV patterns (also considered approved for live card detection)
    cvv_patterns = [
        'CVV',
        'Gateway Rejected: avs_and_cvv',
        'Card Issuer Declined CVV',
        'Gateway Rejected: cvv'
    ]
    
    # Check for Reason: prefix
    if "Reason:" in result:
        reason_part = result.split("Reason:", 1)[1].strip()
        
        for pattern in approved_patterns:
            if pattern in result:
                return "APPROVED", "Approved", True
        
        for pattern in cvv_patterns:
            if pattern in reason_part:
                return "APPROVED", "Approved", True
        
        return "DECLINED", reason_part, False
    
    # Check without Reason: prefix
    for pattern in approved_patterns:
        if pattern in result:
            return "APPROVED", "Approved", True
    
    for pattern in cvv_patterns:
        if pattern in result:
            return "APPROVED", "Approved", True
    
    return "DECLINED", result, False


def format_time_elapsed(seconds: float) -> str:
    """Format elapsed time for display."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


def sanitize_for_telegram(text: str) -> str:
    """
    Sanitize text for Telegram message to avoid Markdown parsing errors.
    
    Args:
        text: Raw text
        
    Returns:
        Sanitized text safe for Telegram
    """
    # Characters that can break Telegram Markdown
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    result = text
    for char in special_chars:
        result = result.replace(char, f'\\{char}')
    
    return result
