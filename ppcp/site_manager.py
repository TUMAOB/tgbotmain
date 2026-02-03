#!/usr/bin/env python3
"""
Site Manager - Handles site rotation, bad site detection, and auto-removal
"""
import os
import threading
import logging
import time
import fcntl
import json
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class SimpleLock:
    """Simple file-based lock using fcntl"""
    def __init__(self, lock_file: str, timeout: int = 10):
        self.lock_file = lock_file
        self.timeout = timeout
        self._lock_fd = None
    
    def __enter__(self):
        self._lock_fd = open(self.lock_file, 'w')
        start_time = time.time()
        while True:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (IOError, OSError):
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Could not acquire lock on {self.lock_file}")
                time.sleep(0.1)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._lock_fd:
            fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            self._lock_fd.close()
        return False

# File paths
SITES_FILE = 'ppcp/sites.txt'
BADSITES_FILE = 'ppcp/badsites.txt'
SITES_LOCK_FILE = 'ppcp/sites.txt.lock'
BADSITES_LOCK_FILE = 'ppcp/badsites.txt.lock'
PPCP_AUTO_REMOVE_SETTINGS_FILE = 'ppcp_auto_remove_settings.json'

# Bad site patterns - responses that indicate site should be removed
BAD_SITE_PATTERNS = [
    # Out of stock / product issues
    'out of stock',
    'out_of_stock',
    'product is out of stock',
    'not available',
    'no longer available',
    'product unavailable',
    'item is no longer available',
    'sold out',
    'currently unavailable',
    'this product is currently out of stock',
    'sorry, this product is unavailable',
    
    # Order creation failures
    'failed to create order',
    'error: failed to create order',
    'cannot create order',
    'order creation failed',
    'unable to create order',
    
    # Site/checkout issues
    'checkout is not available',
    'cart is empty',
    'your cart is currently empty',
    'no items in cart',
    'cannot find product',
    'cannot find product id',
    'product not found',
    'page not found',
    '404 not found',
    'site maintenance',
    'under maintenance',
    'temporarily unavailable',
    
    # Payment gateway issues
    'payment gateway not configured',
    'payment method not available',
    'ppcp not configured',
    'paypal not available',
    
    # Access issues
    'access denied',
    'forbidden',
    'blocked',
    'rate limited',
    'too many requests',
]

# Thread-safe lock for file operations
_file_lock = threading.Lock()


def is_auto_remove_enabled() -> bool:
    """Check if auto-remove is enabled"""
    try:
        if os.path.exists(PPCP_AUTO_REMOVE_SETTINGS_FILE):
            with open(PPCP_AUTO_REMOVE_SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                return settings.get('enabled', True)  # Default to True for backward compatibility
    except Exception as e:
        logger.error(f"Error loading auto-remove settings: {e}")
    return True  # Default to enabled


def load_sites() -> List[str]:
    """Load sites from sites.txt file with thread safety"""
    try:
        with SimpleLock(SITES_LOCK_FILE, timeout=10):
            if os.path.exists(SITES_FILE):
                with open(SITES_FILE, 'r') as f:
                    sites = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                return sites
    except Exception as e:
        logger.error(f"Error loading sites: {e}")
    return []


def save_sites(sites: List[str]) -> bool:
    """Save sites to sites.txt file with thread safety"""
    try:
        with SimpleLock(SITES_LOCK_FILE, timeout=10):
            with open(SITES_FILE, 'w') as f:
                for site in sites:
                    if site.strip():
                        f.write(site.strip() + '\n')
            return True
    except Exception as e:
        logger.error(f"Error saving sites: {e}")
        return False


def load_bad_sites() -> List[str]:
    """Load bad sites from badsites.txt file with thread safety"""
    try:
        with SimpleLock(BADSITES_LOCK_FILE, timeout=10):
            if os.path.exists(BADSITES_FILE):
                with open(BADSITES_FILE, 'r') as f:
                    sites = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                return sites
    except Exception as e:
        logger.error(f"Error loading bad sites: {e}")
    return []


def add_bad_site(site_url: str, reason: str) -> bool:
    """Add a site to badsites.txt and remove from sites.txt"""
    
    # Check if auto-remove is enabled
    if not is_auto_remove_enabled():
        logger.info(f"Auto-remove is disabled. Skipping bad site removal for: {site_url}")
        return False
    
    try:
        # Normalize URL
        site_url = site_url.strip().rstrip('/')
        
        # Add to bad sites
        with SimpleLock(BADSITES_LOCK_FILE, timeout=10):
            # Create file if it doesn't exist
            if not os.path.exists(BADSITES_FILE):
                with open(BADSITES_FILE, 'w') as f:
                    f.write("# Bad sites - automatically detected\n")
                    f.write("# Format: site_url | reason | timestamp\n")
            
            # Check if already in bad sites
            bad_sites = []
            with open(BADSITES_FILE, 'r') as f:
                bad_sites = [line.strip() for line in f if line.strip()]
            
            # Check if site already exists
            site_exists = any(site_url in line for line in bad_sites)
            
            if not site_exists:
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                with open(BADSITES_FILE, 'a') as f:
                    f.write(f"{site_url} | {reason} | {timestamp}\n")
                logger.info(f"Added bad site: {site_url} - Reason: {reason}")
        
        # Remove from good sites
        with SimpleLock(SITES_LOCK_FILE, timeout=10):
            if os.path.exists(SITES_FILE):
                with open(SITES_FILE, 'r') as f:
                    sites = [line.strip() for line in f if line.strip()]
                
                # Filter out the bad site
                original_count = len(sites)
                sites = [s for s in sites if site_url not in s and s not in site_url]
                
                if len(sites) < original_count:
                    with open(SITES_FILE, 'w') as f:
                        for site in sites:
                            if site and not site.startswith('#'):
                                f.write(site + '\n')
                    logger.info(f"Removed {site_url} from sites.txt")
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding bad site: {e}")
        return False


def is_bad_response(response_text: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a response indicates a bad site that should be removed.
    
    Returns:
        Tuple of (is_bad, reason)
    """
    if not response_text:
        return False, None
    
    response_lower = response_text.lower()
    
    for pattern in BAD_SITE_PATTERNS:
        if pattern.lower() in response_lower:
            return True, pattern
    
    return False, None


def check_and_handle_bad_site(site_url: str, response_text: str) -> bool:
    """
    Check if response indicates a bad site and handle accordingly.
    
    Returns:
        True if site was marked as bad, False otherwise
    """
    is_bad, reason = is_bad_response(response_text)
    
    if is_bad:
        add_bad_site(site_url, reason)
        return True
    
    return False


def get_available_sites() -> List[str]:
    """Get list of available (non-bad) sites"""
    sites = load_sites()
    bad_sites = load_bad_sites()
    
    # Filter out bad sites
    available = []
    for site in sites:
        site_clean = site.strip().rstrip('/')
        is_bad = False
        for bad in bad_sites:
            if site_clean in bad or bad.split('|')[0].strip() in site_clean:
                is_bad = True
                break
        if not is_bad:
            available.append(site)
    
    return available


def restore_site(site_url: str) -> bool:
    """Restore a site from badsites.txt back to sites.txt"""
    try:
        site_url = site_url.strip().rstrip('/')
        
        # Remove from bad sites
        with SimpleLock(BADSITES_LOCK_FILE, timeout=10):
            if os.path.exists(BADSITES_FILE):
                with open(BADSITES_FILE, 'r') as f:
                    lines = f.readlines()
                
                with open(BADSITES_FILE, 'w') as f:
                    for line in lines:
                        if site_url not in line:
                            f.write(line)
        
        # Add back to good sites
        with SimpleLock(SITES_LOCK_FILE, timeout=10):
            sites = []
            if os.path.exists(SITES_FILE):
                with open(SITES_FILE, 'r') as f:
                    sites = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            if site_url not in sites:
                sites.append(site_url)
                with open(SITES_FILE, 'w') as f:
                    for site in sites:
                        f.write(site + '\n')
        
        logger.info(f"Restored site: {site_url}")
        return True
        
    except Exception as e:
        logger.error(f"Error restoring site: {e}")
        return False


def get_site_stats() -> dict:
    """Get statistics about sites"""
    sites = load_sites()
    bad_sites = load_bad_sites()
    
    return {
        'total_sites': len(sites),
        'bad_sites': len(bad_sites),
        'available_sites': len(get_available_sites())
    }
