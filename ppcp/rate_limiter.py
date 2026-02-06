#!/usr/bin/env python3
"""
Rate limiter implementation for PPCP checker
"""
import asyncio
import time
from collections import defaultdict, deque
from typing import Optional

class RateLimiter:
    """Token bucket rate limiter for controlling request rates"""
    
    def __init__(self, rate_limit_per_second: int = 10, burst_limit: int = 20):
        self.rate_limit = rate_limit_per_second
        self.burst_limit = burst_limit
        self.tokens = burst_limit
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, blocking if necessary"""
        async with self.lock:
            now = time.time()
            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            new_tokens = elapsed * self.rate_limit
            self.tokens = min(self.burst_limit, self.tokens + new_tokens)
            self.last_refill = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
            else:
                # Calculate wait time needed
                wait_time = (tokens - self.tokens) / self.rate_limit
                await asyncio.sleep(wait_time)
                self.tokens = 0
                self.last_refill = time.time()

class DomainRateLimiter:
    """Rate limiter per domain to avoid overwhelming individual sites"""
    
    def __init__(self, default_rate: int = 5, default_burst: int = 10):
        self.default_rate = default_rate
        self.default_burst = default_burst
        self.limiters = {}
        self.lock = asyncio.Lock()
    
    async def get_limiter(self, domain: str) -> RateLimiter:
        """Get or create rate limiter for domain"""
        async with self.lock:
            if domain not in self.limiters:
                self.limiters[domain] = RateLimiter(self.default_rate, self.default_burst)
            return self.limiters[domain]
    
    async def acquire(self, domain: str, tokens: int = 1) -> None:
        """Acquire tokens for specific domain"""
        limiter = await self.get_limiter(domain)
        await limiter.acquire(tokens)

# Global rate limiter instance - Optimized for bare metal server
# Very high limits for handling thousands of concurrent users
global_rate_limiter = RateLimiter(rate_limit_per_second=500, burst_limit=1000)
domain_rate_limiter = DomainRateLimiter(default_rate=100, default_burst=200)