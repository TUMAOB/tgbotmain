"""
Core module for shared utilities and optimized components.

This module provides:
- Centralized configuration management
- Optimized database access with caching
- HTTP client connection pooling
- Rate limiting for API calls
- Common utility functions
"""

from .config import Config, GatewayConfig, get_config
from .database import DatabaseManager, CachedDatabase, get_db_manager
from .http_client import (
    HTTPClientManager, 
    get_shared_session,
    get_http_client,
    AsyncRequestHelper,
    SyncRequestHelper,
)
from .utils import (
    normalize_card_format,
    country_code_to_emoji,
    get_bin_info_cached,
    generate_random_name,
    generate_random_email,
    get_random_user_agent,
    get_random_address,
    get_country_from_domain,
    parse_proxy_string,
    check_card_status,
    format_time_elapsed,
)
from .rate_limiter import (
    AsyncRateLimiter,
    SyncRateLimiter,
    DomainRateLimiter,
    UserRateLimiter,
    MassCheckLimiter,
    global_rate_limiter,
    domain_rate_limiter,
    user_rate_limiter,
    mass_check_limiter,
)

__all__ = [
    # Config
    'Config',
    'GatewayConfig',
    'get_config',
    
    # Database
    'DatabaseManager',
    'CachedDatabase',
    'get_db_manager',
    
    # HTTP Client
    'HTTPClientManager',
    'get_shared_session',
    'get_http_client',
    'AsyncRequestHelper',
    'SyncRequestHelper',
    
    # Utils
    'normalize_card_format',
    'country_code_to_emoji',
    'get_bin_info_cached',
    'generate_random_name',
    'generate_random_email',
    'get_random_user_agent',
    'get_random_address',
    'get_country_from_domain',
    'parse_proxy_string',
    'check_card_status',
    'format_time_elapsed',
    
    # Rate Limiting
    'AsyncRateLimiter',
    'SyncRateLimiter',
    'DomainRateLimiter',
    'UserRateLimiter',
    'MassCheckLimiter',
    'global_rate_limiter',
    'domain_rate_limiter',
    'user_rate_limiter',
    'mass_check_limiter',
]

__version__ = '1.0.0'
