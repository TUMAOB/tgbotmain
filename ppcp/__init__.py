#!/usr/bin/env python3
"""
PPCP (PayPal Credit Card Payment) Gateway Checker Module

This module provides:
- Async card checking with streaming results
- Bad site detection and auto-removal
- Rate limiting and metrics collection
- Production-optimized configuration
"""

from .site_manager import (
    load_sites,
    save_sites,
    load_bad_sites,
    add_bad_site,
    is_bad_response,
    check_and_handle_bad_site,
    get_available_sites,
    restore_site,
    get_site_stats,
    BAD_SITE_PATTERNS
)

from .rate_limiter import (
    RateLimiter,
    DomainRateLimiter,
    global_rate_limiter,
    domain_rate_limiter
)

from .metrics import (
    MetricsCollector,
    metrics_collector
)

# Note: async_ppcpgatewaycvv and ppcpgatewaycvv require aiohttp/requests
# Import them only when needed to avoid import errors if dependencies are missing

__all__ = [
    # Site management
    'load_sites',
    'save_sites', 
    'load_bad_sites',
    'add_bad_site',
    'is_bad_response',
    'check_and_handle_bad_site',
    'get_available_sites',
    'restore_site',
    'get_site_stats',
    'BAD_SITE_PATTERNS',
    
    # Rate limiting
    'RateLimiter',
    'DomainRateLimiter',
    'global_rate_limiter',
    'domain_rate_limiter',
    
    # Metrics
    'MetricsCollector',
    'metrics_collector',
]

__version__ = '2.0.0'
