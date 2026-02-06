"""
Enhanced rate limiter with token bucket algorithm and per-domain limiting.
Optimized for high-concurrency card checking operations.
"""
import asyncio
import time
import threading
from collections import defaultdict
from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""
    rate: float  # Tokens per second
    capacity: float  # Maximum tokens
    tokens: float = field(default=0.0)
    last_update: float = field(default_factory=time.time)
    
    def __post_init__(self):
        self.tokens = self.capacity
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
    
    def consume(self, tokens: float = 1.0) -> float:
        """
        Try to consume tokens. Returns wait time if not enough tokens.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            Wait time in seconds (0 if tokens were available)
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return 0.0
        
        # Calculate wait time
        deficit = tokens - self.tokens
        wait_time = deficit / self.rate
        return wait_time


class AsyncRateLimiter:
    """
    Async-compatible rate limiter using token bucket algorithm.
    Thread-safe and optimized for high concurrency.
    """
    
    def __init__(
        self, 
        rate_per_second: float = 10.0, 
        burst_capacity: float = 20.0
    ):
        """
        Initialize rate limiter.
        
        Args:
            rate_per_second: Sustained rate of requests per second
            burst_capacity: Maximum burst size
        """
        self.bucket = TokenBucket(rate=rate_per_second, capacity=burst_capacity)
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: float = 1.0) -> None:
        """
        Acquire tokens, waiting if necessary.
        
        Args:
            tokens: Number of tokens to acquire
        """
        async with self._lock:
            wait_time = self.bucket.consume(tokens)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                # Consume again after waiting
                self.bucket.consume(tokens)
    
    def try_acquire(self, tokens: float = 1.0) -> bool:
        """
        Try to acquire tokens without waiting.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False otherwise
        """
        wait_time = self.bucket.consume(tokens)
        return wait_time == 0


class SyncRateLimiter:
    """
    Thread-safe synchronous rate limiter.
    """
    
    def __init__(
        self, 
        rate_per_second: float = 10.0, 
        burst_capacity: float = 20.0
    ):
        self.bucket = TokenBucket(rate=rate_per_second, capacity=burst_capacity)
        self._lock = threading.Lock()
    
    def acquire(self, tokens: float = 1.0) -> None:
        """Acquire tokens, blocking if necessary."""
        with self._lock:
            wait_time = self.bucket.consume(tokens)
            if wait_time > 0:
                time.sleep(wait_time)
                self.bucket.consume(tokens)
    
    def try_acquire(self, tokens: float = 1.0) -> bool:
        """Try to acquire tokens without blocking."""
        with self._lock:
            wait_time = self.bucket.consume(tokens)
            return wait_time == 0


class DomainRateLimiter:
    """
    Per-domain rate limiter to avoid overwhelming individual sites.
    Creates separate rate limiters for each domain.
    """
    
    def __init__(
        self, 
        default_rate: float = 5.0, 
        default_burst: float = 10.0
    ):
        """
        Initialize domain rate limiter.
        
        Args:
            default_rate: Default rate per second for each domain
            default_burst: Default burst capacity for each domain
        """
        self.default_rate = default_rate
        self.default_burst = default_burst
        self._limiters: Dict[str, AsyncRateLimiter] = {}
        self._lock = asyncio.Lock()
        
        # Custom rates for specific domains
        self._custom_rates: Dict[str, tuple] = {}
    
    def set_domain_rate(self, domain: str, rate: float, burst: float = None) -> None:
        """
        Set custom rate for a specific domain.
        
        Args:
            domain: Domain name
            rate: Rate per second
            burst: Burst capacity (defaults to 2x rate)
        """
        self._custom_rates[domain] = (rate, burst or rate * 2)
    
    async def _get_limiter(self, domain: str) -> AsyncRateLimiter:
        """Get or create rate limiter for domain."""
        async with self._lock:
            if domain not in self._limiters:
                rate, burst = self._custom_rates.get(
                    domain, 
                    (self.default_rate, self.default_burst)
                )
                self._limiters[domain] = AsyncRateLimiter(rate, burst)
            return self._limiters[domain]
    
    async def acquire(self, domain: str, tokens: float = 1.0) -> None:
        """
        Acquire tokens for a specific domain.
        
        Args:
            domain: Domain name
            tokens: Number of tokens to acquire
        """
        limiter = await self._get_limiter(domain)
        await limiter.acquire(tokens)
    
    def cleanup_old_limiters(self, max_age: float = 3600.0) -> int:
        """
        Remove limiters that haven't been used recently.
        
        Args:
            max_age: Maximum age in seconds
            
        Returns:
            Number of limiters removed
        """
        # This is a simplified cleanup - in production you'd track last access time
        return 0


class UserRateLimiter:
    """
    Per-user rate limiter for bot commands.
    Thread-safe for use with Telegram bot handlers.
    """
    
    def __init__(self, rate_limit_seconds: float = 1.0):
        """
        Initialize user rate limiter.
        
        Args:
            rate_limit_seconds: Minimum seconds between requests per user
        """
        self.rate_limit_seconds = rate_limit_seconds
        self._last_request: Dict[int, float] = {}
        self._lock = threading.Lock()
    
    def check_rate_limit(self, user_id: int) -> tuple[bool, float]:
        """
        Check if user is rate limited.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Tuple of (is_allowed, wait_time)
        """
        with self._lock:
            now = time.time()
            last_time = self._last_request.get(user_id, 0)
            elapsed = now - last_time
            
            if elapsed >= self.rate_limit_seconds:
                self._last_request[user_id] = now
                return True, 0.0
            
            wait_time = self.rate_limit_seconds - elapsed
            return False, wait_time
    
    def update_last_request(self, user_id: int) -> None:
        """Update last request time for user."""
        with self._lock:
            self._last_request[user_id] = time.time()
    
    def cleanup_old_entries(self, max_age: float = 3600.0) -> int:
        """
        Remove entries older than max_age.
        
        Args:
            max_age: Maximum age in seconds
            
        Returns:
            Number of entries removed
        """
        with self._lock:
            now = time.time()
            old_users = [
                uid for uid, last_time in self._last_request.items()
                if now - last_time > max_age
            ]
            for uid in old_users:
                del self._last_request[uid]
            return len(old_users)


class MassCheckLimiter:
    """
    Limiter for mass check operations to prevent system overload.
    """
    
    def __init__(
        self, 
        max_per_user: int = 1, 
        max_total: int = 5
    ):
        """
        Initialize mass check limiter.
        
        Args:
            max_per_user: Maximum concurrent mass checks per user
            max_total: Maximum total concurrent mass checks
        """
        self.max_per_user = max_per_user
        self.max_total = max_total
        self._active_checks: Dict[int, Dict] = {}
        self._lock = threading.Lock()
    
    def can_start(self, user_id: int, is_admin: bool = False) -> tuple[bool, Optional[str]]:
        """
        Check if user can start a mass check.
        
        Args:
            user_id: User ID
            is_admin: Whether user is admin (bypasses limits)
            
        Returns:
            Tuple of (can_start, error_message)
        """
        if is_admin:
            return True, None
        
        with self._lock:
            # Check user's concurrent checks
            user_count = sum(1 for uid in self._active_checks if uid == user_id)
            if user_count >= self.max_per_user:
                return False, "You already have a mass check in progress. Please wait for it to complete."
            
            # Check total concurrent checks
            if len(self._active_checks) >= self.max_total:
                return False, f"System is busy with {len(self._active_checks)} mass checks. Please try again later."
        
        return True, None
    
    def register(self, user_id: int, total_cards: int) -> None:
        """Register a new mass check."""
        with self._lock:
            self._active_checks[user_id] = {
                'started': time.time(),
                'total_cards': total_cards
            }
    
    def unregister(self, user_id: int) -> None:
        """Unregister a completed mass check."""
        with self._lock:
            self._active_checks.pop(user_id, None)
    
    def get_active_count(self) -> int:
        """Get total number of active mass checks."""
        with self._lock:
            return len(self._active_checks)
    
    def get_user_count(self, user_id: int) -> int:
        """Get number of active mass checks for a user."""
        with self._lock:
            return sum(1 for uid in self._active_checks if uid == user_id)
    
    def get_status(self) -> Dict:
        """Get status of all active mass checks."""
        with self._lock:
            return {
                'total': len(self._active_checks),
                'max_total': self.max_total,
                'checks': dict(self._active_checks)
            }


# Global instances - Optimized for bare metal server with thousands of concurrent users
global_rate_limiter = AsyncRateLimiter(rate_per_second=500.0, burst_capacity=1000.0)
domain_rate_limiter = DomainRateLimiter(default_rate=100.0, default_burst=200.0)
user_rate_limiter = UserRateLimiter(rate_limit_seconds=0.5)
mass_check_limiter = MassCheckLimiter(max_per_user=5, max_total=200)
