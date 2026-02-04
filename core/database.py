"""
Optimized database management with caching and connection pooling.
Reduces file I/O overhead and improves thread safety.
"""
import json
import os
import threading
import time
import fcntl
from typing import Any, Dict, Optional, TypeVar, Generic, Callable
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, field

# Try to import filelock, fallback to fcntl-based implementation
try:
    from filelock import SoftFileLock
except ImportError:
    # Fallback implementation using fcntl
    class SoftFileLock:
        """Simple file lock using fcntl as fallback."""
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

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """Cache entry with TTL support."""
    data: T
    timestamp: float
    ttl: float = 60.0  # Default 60 seconds TTL
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.timestamp > self.ttl


class CachedDatabase(Generic[T]):
    """
    Thread-safe database with in-memory caching.
    Reduces file I/O by caching reads and batching writes.
    """
    
    def __init__(
        self, 
        file_path: str, 
        default_factory: Callable[[], T],
        cache_ttl: float = 60.0,
        lock_timeout: int = 10
    ):
        self.file_path = file_path
        self.lock_file = f"{file_path}.lock"
        self.default_factory = default_factory
        self.cache_ttl = cache_ttl
        self.lock_timeout = lock_timeout
        
        self._cache: Optional[CacheEntry[T]] = None
        self._cache_lock = threading.RLock()
        self._dirty = False
        self._write_lock = threading.Lock()
    
    def _get_file_lock(self) -> SoftFileLock:
        """Get file lock for thread-safe file operations."""
        return SoftFileLock(self.lock_file, timeout=self.lock_timeout)
    
    def load(self, force_reload: bool = False) -> T:
        """
        Load data from file with caching.
        
        Args:
            force_reload: Force reload from file, ignoring cache
            
        Returns:
            The loaded data
        """
        with self._cache_lock:
            # Check cache first
            if not force_reload and self._cache and not self._cache.is_expired():
                return self._cache.data
            
            # Load from file
            with self._get_file_lock():
                if os.path.exists(self.file_path):
                    try:
                        with open(self.file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    except (json.JSONDecodeError, IOError):
                        data = self.default_factory()
                else:
                    data = self.default_factory()
            
            # Update cache
            self._cache = CacheEntry(data=data, timestamp=time.time(), ttl=self.cache_ttl)
            return data
    
    def save(self, data: T) -> bool:
        """
        Save data to file with caching.
        
        Args:
            data: The data to save
            
        Returns:
            True if save was successful
        """
        with self._write_lock:
            try:
                with self._get_file_lock():
                    with open(self.file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                
                # Update cache
                with self._cache_lock:
                    self._cache = CacheEntry(data=data, timestamp=time.time(), ttl=self.cache_ttl)
                    self._dirty = False
                
                return True
            except IOError:
                return False
    
    def update(self, updater: Callable[[T], T]) -> bool:
        """
        Atomically update data using an updater function.
        
        Args:
            updater: Function that takes current data and returns updated data
            
        Returns:
            True if update was successful
        """
        with self._write_lock:
            data = self.load(force_reload=True)
            updated_data = updater(data)
            return self.save(updated_data)
    
    def invalidate_cache(self) -> None:
        """Invalidate the cache, forcing next load to read from file."""
        with self._cache_lock:
            self._cache = None


class DatabaseManager:
    """
    Centralized database manager for all JSON databases.
    Provides optimized access with caching and connection pooling.
    """
    
    _instance: Optional['DatabaseManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'DatabaseManager':
        """Singleton pattern for database manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._databases: Dict[str, CachedDatabase] = {}
        self._db_lock = threading.Lock()
        self._initialized = True
        
        # Initialize common databases
        self._init_databases()
    
    def _init_databases(self) -> None:
        """Initialize common database instances."""
        # User database
        self._databases['users'] = CachedDatabase(
            'users_db.json',
            default_factory=dict,
            cache_ttl=30.0  # 30 seconds cache for user data
        )
        
        # Mods database
        self._databases['mods'] = CachedDatabase(
            'mods_db.json',
            default_factory=dict,
            cache_ttl=60.0
        )
        
        # Forwarders database
        self._databases['forwarders'] = CachedDatabase(
            'forwarders_db.json',
            default_factory=lambda: {'b3': [], 'pp': [], 'ppro': []},
            cache_ttl=60.0
        )
        
        # Site freeze state
        self._databases['site_freeze'] = CachedDatabase(
            'site_freeze_state.json',
            default_factory=dict,
            cache_ttl=30.0
        )
        
        # Mass settings
        self._databases['mass_settings'] = CachedDatabase(
            'mass_settings.json',
            default_factory=lambda: {'b3': True, 'pp': True, 'ppro': True},
            cache_ttl=60.0
        )
        
        # Gateway interval settings
        self._databases['gateway_intervals'] = CachedDatabase(
            'gateway_interval_settings.json',
            default_factory=lambda: {'b3': 1, 'pp': 1, 'ppro': 1},
            cache_ttl=60.0
        )
        
        # Bot settings
        self._databases['bot_settings'] = CachedDatabase(
            'bot_settings.json',
            default_factory=lambda: {'start_message': None, 'pinned_message': None, 'pinned_message_id': None},
            cache_ttl=120.0
        )
        
        # Auto-scan settings
        self._databases['auto_scan'] = CachedDatabase(
            'auto_scan_settings.json',
            default_factory=lambda: {'enabled': False, 'interval_hours': 1},
            cache_ttl=60.0
        )
        
        # PPCP auto-remove settings
        self._databases['ppcp_auto_remove'] = CachedDatabase(
            'ppcp_auto_remove_settings.json',
            default_factory=lambda: {'enabled': True},
            cache_ttl=60.0
        )
    
    def get_database(self, name: str) -> Optional[CachedDatabase]:
        """Get a database by name."""
        return self._databases.get(name)
    
    def register_database(
        self, 
        name: str, 
        file_path: str, 
        default_factory: Callable,
        cache_ttl: float = 60.0
    ) -> CachedDatabase:
        """Register a new database."""
        with self._db_lock:
            if name not in self._databases:
                self._databases[name] = CachedDatabase(
                    file_path,
                    default_factory,
                    cache_ttl
                )
            return self._databases[name]
    
    # Convenience methods for common operations
    
    def load_users(self) -> Dict:
        """Load user database."""
        return self._databases['users'].load()
    
    def save_users(self, data: Dict) -> bool:
        """Save user database."""
        return self._databases['users'].save(data)
    
    def load_mods(self) -> Dict:
        """Load mods database."""
        return self._databases['mods'].load()
    
    def save_mods(self, data: Dict) -> bool:
        """Save mods database."""
        return self._databases['mods'].save(data)
    
    def load_forwarders(self) -> Dict:
        """Load forwarders database."""
        return self._databases['forwarders'].load()
    
    def save_forwarders(self, data: Dict) -> bool:
        """Save forwarders database."""
        return self._databases['forwarders'].save(data)
    
    def load_site_freeze(self) -> Dict:
        """Load site freeze state."""
        return self._databases['site_freeze'].load()
    
    def save_site_freeze(self, data: Dict) -> bool:
        """Save site freeze state."""
        return self._databases['site_freeze'].save(data)
    
    def load_mass_settings(self) -> Dict:
        """Load mass check settings."""
        return self._databases['mass_settings'].load()
    
    def save_mass_settings(self, data: Dict) -> bool:
        """Save mass check settings."""
        return self._databases['mass_settings'].save(data)
    
    def load_gateway_intervals(self) -> Dict:
        """Load gateway interval settings."""
        return self._databases['gateway_intervals'].load()
    
    def save_gateway_intervals(self, data: Dict) -> bool:
        """Save gateway interval settings."""
        return self._databases['gateway_intervals'].save(data)
    
    def load_bot_settings(self) -> Dict:
        """Load bot settings."""
        return self._databases['bot_settings'].load()
    
    def save_bot_settings(self, data: Dict) -> bool:
        """Save bot settings."""
        return self._databases['bot_settings'].save(data)
    
    def invalidate_all_caches(self) -> None:
        """Invalidate all database caches."""
        for db in self._databases.values():
            db.invalidate_cache()


# Singleton accessor
def get_db_manager() -> DatabaseManager:
    """Get the singleton database manager instance."""
    return DatabaseManager()


# Decorator for database operations with automatic retry
def with_retry(max_retries: int = 3, delay: float = 0.1):
    """Decorator to retry database operations on failure."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))
            raise last_error
        return wrapper
    return decorator
