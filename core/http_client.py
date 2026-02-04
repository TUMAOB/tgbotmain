"""
Optimized HTTP client management with connection pooling and session reuse.
Reduces connection overhead and improves performance for high-volume requests.
"""
import asyncio
import ssl
import threading
import time
from typing import Dict, Optional, Any
from functools import lru_cache
import logging

# Optional imports with graceful fallbacks
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    HTTPAdapter = None
    Retry = None
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


class HTTPClientManager:
    """
    Manages HTTP sessions with connection pooling for both sync and async operations.
    Implements singleton pattern for efficient resource usage.
    """
    
    _instance: Optional['HTTPClientManager'] = None
    _lock = threading.Lock()
    
    # Default configuration
    DEFAULT_TIMEOUT = 15
    DEFAULT_MAX_RETRIES = 2
    DEFAULT_BACKOFF_FACTOR = 0.3
    DEFAULT_POOL_CONNECTIONS = 20
    DEFAULT_POOL_MAXSIZE = 50
    DEFAULT_CONNECTION_LIMIT = 100
    DEFAULT_CONNECTION_LIMIT_PER_HOST = 20
    
    def __new__(cls) -> 'HTTPClientManager':
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._sync_sessions: Dict[str, requests.Session] = {}
        self._async_session: Optional[aiohttp.ClientSession] = None
        self._session_lock = threading.Lock()
        self._async_lock = asyncio.Lock() if asyncio.get_event_loop().is_running() else None
        self._initialized = True
    
    def _create_retry_strategy(self, max_retries: int = None):
        """Create retry strategy for requests."""
        if not REQUESTS_AVAILABLE or Retry is None:
            return None
        return Retry(
            total=max_retries or self.DEFAULT_MAX_RETRIES,
            backoff_factor=self.DEFAULT_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
    
    def get_sync_session(
        self, 
        name: str = 'default',
        timeout: int = None,
        max_retries: int = None,
        pool_connections: int = None,
        pool_maxsize: int = None
    ):
        """
        Get or create a named sync session with connection pooling.
        
        Args:
            name: Session name for reuse
            timeout: Request timeout
            max_retries: Maximum retry attempts
            pool_connections: Number of connection pools
            pool_maxsize: Maximum connections per pool
            
        Returns:
            Configured requests.Session or None if requests not available
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("requests library not available")
            return None
            
        with self._session_lock:
            if name not in self._sync_sessions:
                session = requests.Session()
                
                # Configure retry strategy
                retry_strategy = self._create_retry_strategy(max_retries)
                
                # Configure adapter with connection pooling
                adapter = HTTPAdapter(
                    max_retries=retry_strategy,
                    pool_connections=pool_connections or self.DEFAULT_POOL_CONNECTIONS,
                    pool_maxsize=pool_maxsize or self.DEFAULT_POOL_MAXSIZE
                )
                
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                
                # Set default timeout
                session.timeout = timeout or self.DEFAULT_TIMEOUT
                
                self._sync_sessions[name] = session
            
            return self._sync_sessions[name]
    
    async def get_async_session(
        self,
        connection_limit: int = None,
        connection_limit_per_host: int = None,
        timeout: int = None
    ):
        """
        Get or create the async session with optimized connection pooling.
        
        Args:
            connection_limit: Total connection limit
            connection_limit_per_host: Per-host connection limit
            timeout: Request timeout
            
        Returns:
            Configured aiohttp.ClientSession or None if aiohttp not available
        """
        if not AIOHTTP_AVAILABLE:
            logger.warning("aiohttp library not available")
            return None
            
        if self._async_session is None or self._async_session.closed:
            # Create SSL context that doesn't verify certificates
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create connector with connection pooling
            connector = aiohttp.TCPConnector(
                limit=connection_limit or self.DEFAULT_CONNECTION_LIMIT,
                limit_per_host=connection_limit_per_host or self.DEFAULT_CONNECTION_LIMIT_PER_HOST,
                ttl_dns_cache=600,  # Cache DNS for 10 minutes
                use_dns_cache=True,
                ssl=ssl_context,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
                force_close=False
            )
            
            # Create timeout configuration
            client_timeout = aiohttp.ClientTimeout(
                total=timeout or self.DEFAULT_TIMEOUT,
                connect=5,
                sock_read=10
            )
            
            self._async_session = aiohttp.ClientSession(
                connector=connector,
                timeout=client_timeout,
                trust_env=True
            )
        
        return self._async_session
    
    async def close_async_session(self) -> None:
        """Close the async session."""
        if self._async_session and not self._async_session.closed:
            await self._async_session.close()
            self._async_session = None
    
    def close_sync_sessions(self) -> None:
        """Close all sync sessions."""
        with self._session_lock:
            for session in self._sync_sessions.values():
                session.close()
            self._sync_sessions.clear()
    
    async def cleanup(self) -> None:
        """Cleanup all resources."""
        await self.close_async_session()
        self.close_sync_sessions()


# Singleton accessor
def get_http_client() -> HTTPClientManager:
    """Get the singleton HTTP client manager."""
    return HTTPClientManager()


# Convenience function for getting shared session
def get_shared_session(name: str = 'default'):
    """Get a shared sync session."""
    return get_http_client().get_sync_session(name)


async def get_shared_async_session():
    """Get the shared async session."""
    return await get_http_client().get_async_session()


class AsyncRequestHelper:
    """
    Helper class for making async HTTP requests with retry logic and rate limiting.
    """
    
    def __init__(
        self,
        session,  # aiohttp.ClientSession
        max_retries: int = 2,
        retry_delay: float = 0.5,
        rate_limiter = None
    ):
        self.session = session
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limiter = rate_limiter
    
    async def get(
        self, 
        url: str, 
        headers: Dict[str, str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Make GET request with retry logic.
        
        Args:
            url: Request URL
            headers: Request headers
            **kwargs: Additional arguments for aiohttp
            
        Returns:
            Response text or None on failure
        """
        for attempt in range(self.max_retries):
            try:
                if self.rate_limiter:
                    await self.rate_limiter.acquire()
                
                async with self.session.get(url, headers=headers, **kwargs) as response:
                    return await response.text()
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"GET request failed after {self.max_retries} attempts: {url} - {e}")
                    return None
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        return None
    
    async def post(
        self,
        url: str,
        headers: Dict[str, str] = None,
        data: Any = None,
        json_data: Any = None,
        **kwargs
    ) -> Optional[str]:
        """
        Make POST request with retry logic.
        
        Args:
            url: Request URL
            headers: Request headers
            data: Form data
            json_data: JSON data
            **kwargs: Additional arguments for aiohttp
            
        Returns:
            Response text or None on failure
        """
        for attempt in range(self.max_retries):
            try:
                if self.rate_limiter:
                    await self.rate_limiter.acquire()
                
                async with self.session.post(
                    url, 
                    headers=headers, 
                    data=data, 
                    json=json_data,
                    **kwargs
                ) as response:
                    return await response.text()
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"POST request failed after {self.max_retries} attempts: {url} - {e}")
                    return None
                await asyncio.sleep(self.retry_delay * (2 ** attempt))
        return None


class SyncRequestHelper:
    """
    Helper class for making sync HTTP requests with retry logic.
    """
    
    def __init__(
        self,
        session = None,  # requests.Session
        timeout: int = 15,
        verify_ssl: bool = False
    ):
        self.session = session or (get_shared_session() if REQUESTS_AVAILABLE else None)
        self.timeout = timeout
        self.verify_ssl = verify_ssl
    
    def get(
        self,
        url: str,
        headers: Dict[str, str] = None,
        cookies: Dict[str, str] = None,
        proxies: Dict[str, str] = None,
        **kwargs
    ) -> Optional[Any]:
        """
        Make GET request.
        
        Args:
            url: Request URL
            headers: Request headers
            cookies: Request cookies
            proxies: Proxy configuration
            **kwargs: Additional arguments
            
        Returns:
            Response object or None on failure
        """
        try:
            return self.session.get(
                url,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
                timeout=self.timeout,
                verify=self.verify_ssl,
                **kwargs
            )
        except Exception as e:
            logger.error(f"GET request failed: {url} - {e}")
            return None
    
    def post(
        self,
        url: str,
        headers: Dict[str, str] = None,
        cookies: Dict[str, str] = None,
        data: Any = None,
        json_data: Any = None,
        proxies: Dict[str, str] = None,
        **kwargs
    ) -> Optional[Any]:
        """
        Make POST request.
        
        Args:
            url: Request URL
            headers: Request headers
            cookies: Request cookies
            data: Form data
            json_data: JSON data
            proxies: Proxy configuration
            **kwargs: Additional arguments
            
        Returns:
            Response object or None on failure
        """
        try:
            return self.session.post(
                url,
                headers=headers,
                cookies=cookies,
                data=data,
                json=json_data,
                proxies=proxies,
                timeout=self.timeout,
                verify=self.verify_ssl,
                **kwargs
            )
        except Exception as e:
            logger.error(f"POST request failed: {url} - {e}")
            return None
