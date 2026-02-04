"""
Centralized configuration management for the card checker bot.
Eliminates scattered constants and provides environment-based configuration.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from functools import lru_cache


@dataclass(frozen=True)
class GatewayConfig:
    """Configuration for a specific gateway."""
    name: str
    timeout: int = 20
    max_retries: int = 2
    retry_delay: float = 0.5
    rate_limit_per_second: int = 10
    connection_limit: int = 100
    connection_limit_per_host: int = 20


@dataclass
class Config:
    """
    Centralized configuration with environment variable support.
    Uses dataclass for clean, type-safe configuration.
    """
    # Admin settings
    ADMIN_ID: int = field(default_factory=lambda: int(os.getenv('ADMIN_ID', '7405188060')))
    
    # Rate limiting
    RATE_LIMIT_SECONDS: float = field(default_factory=lambda: float(os.getenv('RATE_LIMIT_SECONDS', '1')))
    
    # Mass check limits
    MAX_CONCURRENT_MASS_CHECKS_PER_USER: int = 1
    MAX_TOTAL_CONCURRENT_MASS_CHECKS: int = 5
    
    # File paths - centralized for easy management
    MODS_DB_FILE: str = 'mods_db.json'
    USER_DB_FILE: str = 'users_db.json'
    AUTO_SCAN_SETTINGS_FILE: str = 'auto_scan_settings.json'
    PPCP_AUTO_REMOVE_SETTINGS_FILE: str = 'ppcp_auto_remove_settings.json'
    MASS_SETTINGS_FILE: str = 'mass_settings.json'
    GATEWAY_INTERVAL_SETTINGS_FILE: str = 'gateway_interval_settings.json'
    BOT_SETTINGS_FILE: str = 'bot_settings.json'
    SITE_FREEZE_FILE: str = 'site_freeze_state.json'
    FORWARDERS_DB_FILE: str = 'forwarders_db.json'
    
    # Forward channel
    FORWARD_CHANNEL_ID: Optional[int] = field(
        default_factory=lambda: int(os.getenv('FORWARD_CHANNEL_ID', '-1003865829143'))
    )
    
    # HTTP settings
    REQUEST_TIMEOUT: int = field(default_factory=lambda: int(os.getenv('REQUEST_TIMEOUT', '15')))
    MAX_CONCURRENT_REQUESTS: int = field(default_factory=lambda: int(os.getenv('MAX_CONCURRENT_REQUESTS', '50')))
    CONNECTION_LIMIT: int = field(default_factory=lambda: int(os.getenv('CONNECTION_LIMIT', '100')))
    CONNECTION_LIMIT_PER_HOST: int = field(default_factory=lambda: int(os.getenv('CONNECTION_LIMIT_PER_HOST', '20')))
    
    # BIN lookup
    BIN_CHECK_TIMEOUT: int = field(default_factory=lambda: int(os.getenv('BIN_CHECK_TIMEOUT', '5')))
    BIN_CACHE_SIZE: int = field(default_factory=lambda: int(os.getenv('BIN_CACHE_SIZE', '1000')))
    BIN_CACHE_TTL: int = 3600  # 1 hour
    
    # Valid check intervals
    VALID_CHECK_INTERVALS: List[int] = field(default_factory=lambda: [1, 5, 10, 15, 20, 30])
    
    # Gateway configurations
    GATEWAYS: Dict[str, GatewayConfig] = field(default_factory=lambda: {
        'b3': GatewayConfig(name='Braintree Auth', timeout=20),
        'pp': GatewayConfig(name='PPCP', timeout=15, rate_limit_per_second=20),
        'ppro': GatewayConfig(name='PayPal Pro', timeout=25),
    })
    
    def get_lock_file(self, db_file: str) -> str:
        """Get the lock file path for a database file."""
        return f"{db_file}.lock"
    
    def get_gateway_config(self, gateway: str) -> GatewayConfig:
        """Get configuration for a specific gateway."""
        return self.GATEWAYS.get(gateway, self.GATEWAYS['b3'])


# Singleton instance
@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get the singleton configuration instance."""
    return Config()


# Country emoji mapping - moved from auth.py for reuse
COUNTRY_EMOJI_MAP: Dict[str, str] = {
    'PH': '🇵🇭', 'US': '🇺🇸', 'GB': '🇬🇧', 'CA': '🇨🇦', 'AU': '🇦🇺',
    'DE': '🇩🇪', 'FR': '🇫🇷', 'IN': '🇮🇳', 'JP': '🇯🇵', 'CN': '🇨🇳',
    'BR': '🇧🇷', 'RU': '🇷🇺', 'ZA': '🇿🇦', 'NG': '🇳🇬', 'MX': '🇲🇽',
    'IT': '🇮🇹', 'ES': '🇪🇸', 'NL': '🇳🇱', 'SE': '🇸🇪', 'CH': '🇨🇭',
    'KR': '🇰🇷', 'SG': '🇸🇬', 'NZ': '🇳🇿', 'IE': '🇮🇪', 'BE': '🇧🇪',
    'AT': '🇦🇹', 'DK': '🇩🇰', 'NO': '🇳🇴', 'FI': '🇫🇮', 'PL': '🇵🇱',
    'CZ': '🇨🇿', 'PT': '🇵🇹', 'GR': '🇬🇷', 'HU': '🇭🇺', 'RO': '🇷🇴',
    'TR': '🇹🇷', 'IL': '🇮🇱', 'AE': '🇦🇪', 'SA': '🇸🇦', 'EG': '🇪🇬',
    'AR': '🇦🇷', 'CL': '🇨🇱', 'CO': '🇨🇴', 'PE': '🇵🇪', 'VE': '🇻🇪',
    'TH': '🇹🇭', 'MY': '🇲🇾', 'ID': '🇮🇩', 'VN': '🇻🇳', 'HK': '🇭🇰',
}


# Address data - consolidated from multiple files
ADDRESS_DATA: Dict[str, List[Dict[str, str]]] = {
    'NZ': [
        {'street': '248 Princes Street', 'city': 'Grafton', 'zip': '1010', 'state': 'Auckland', 'phone': '(028) 8784-059'},
        {'street': '75 Queen Street', 'city': 'Auckland', 'zip': '1010', 'state': 'Auckland', 'phone': '(029) 1234-567'},
    ],
    'AU': [
        {'street': '123 George Street', 'city': 'Sydney', 'zip': '2000', 'state': 'NSW', 'phone': '+61 2 1234 5678'},
        {'street': '456 Collins Street', 'city': 'Melbourne', 'zip': '3000', 'state': 'VIC', 'phone': '+61 3 8765 4321'},
    ],
    'GB': [
        {'street': '10 Downing Street', 'city': 'London', 'zip': 'SW1A 2AA', 'state': '', 'phone': '+44 20 7925 0918'},
        {'street': '221B Baker Street', 'city': 'London', 'zip': 'NW1 6XE', 'state': '', 'phone': '+44 20 7224 3688'},
    ],
    'CA': [
        {'street': '123 Main Street', 'city': 'Toronto', 'zip': 'M5H 2N2', 'state': 'Ontario', 'phone': '(416) 555-0123'},
        {'street': '456 Maple Avenue', 'city': 'Vancouver', 'zip': 'V6E 1B5', 'state': 'British Columbia', 'phone': '(604) 555-7890'},
    ],
    'US': [
        {'street': '1600 Pennsylvania Avenue NW', 'city': 'Washington', 'zip': '20500', 'state': 'DC', 'phone': '+1 202-456-1111'},
        {'street': '1 Infinite Loop', 'city': 'Cupertino', 'zip': '95014', 'state': 'CA', 'phone': '+1 408-996-1010'},
        {'street': '350 Fifth Avenue', 'city': 'New York', 'zip': '10118', 'state': 'NY', 'phone': '+1 212-736-3100'},
    ],
    'JP': [
        {'street': '1 Chome-1-2 Oshiage', 'city': 'Sumida City, Tokyo', 'zip': '131-0045', 'state': 'Tokyo', 'phone': '+81 3-1234-5678'},
    ],
    'SG': [
        {'street': '10 Anson Road', 'city': 'Singapore', 'zip': '079903', 'state': 'Central Region', 'phone': '(+65) 6221-1234'},
    ],
    'MY': [
        {'street': 'No 56, Jalan Bukit Bintang', 'city': 'Kuala Lumpur', 'zip': '55100', 'state': 'Wilayah Persekutuan', 'phone': '+60 3-1234 5678'},
    ],
    'TH': [
        {'street': '123 Sukhumvit Road', 'city': 'Bangkok', 'zip': '10110', 'state': 'Bangkok', 'phone': '(+66) 2-123-4567'},
    ],
    'NL': [
        {'street': '1 Dam Square', 'city': 'Amsterdam', 'zip': '1012 JS', 'state': 'North Holland', 'phone': '(+31) 20-555-1234'},
    ],
    'ZA': [
        {'street': '10 Adderley Street', 'city': 'Cape Town', 'zip': '8000', 'state': 'Western Cape', 'phone': '(+27) 21-123-4567'},
    ],
    'HK': [
        {'street': "1 Queen's Road Central", 'city': 'Central', 'zip': '', 'state': 'Hong Kong Island', 'phone': '(+852) 2523-1234'},
    ],
    'PH': [
        {'street': '1234 Makati Ave', 'city': 'Makati', 'zip': '1200', 'state': 'Metro Manila', 'phone': '+63 2 1234 5678'},
    ],
}


# Name data for random generation
FIRST_NAMES: List[str] = [
    'John', 'Kyla', 'Sarah', 'Michael', 'Emma', 'James', 'Olivia', 'William', 'Ava', 'Benjamin',
    'Isabella', 'Jacob', 'Lily', 'Daniel', 'Mia', 'Alexander', 'Charlotte', 'Samuel', 'Sophia', 'Matthew',
]

LAST_NAMES: List[str] = [
    'Smith', 'Johnson', 'Williams', 'Jones', 'Brown', 'Davis', 'Miller', 'Wilson', 'Moore', 'Taylor',
    'Anderson', 'Thomas', 'Jackson', 'White', 'Harris', 'Martin', 'Thompson', 'Garcia', 'Martinez', 'Roberts',
]

EMAIL_DOMAINS: List[str] = ['gmail.com', 'yahoo.com', 'outlook.com', 'icloud.com', 'hotmail.com', 'protonmail.com']


# User agents for rotation
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Mobile Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
]
