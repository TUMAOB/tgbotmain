#!/usr/bin/env python3
"""
Gateway Usage Statistics Tracker
Tracks threads/bots usage per gateway for monitoring and admin panel display.
Thread-safe implementation with persistent storage.
"""
import json
import os
import time
import threading
import fcntl
from typing import Dict, Any, Optional
from collections import defaultdict
from datetime import datetime

# Stats file path
GATEWAY_STATS_FILE = 'gateway_stats.json'

# Thread-safe lock for in-memory stats
_stats_lock = threading.Lock()

# In-memory stats cache
_stats_cache: Dict[str, Any] = None
_stats_cache_time: float = 0
STATS_CACHE_TTL = 5  # 5 seconds cache TTL


class FileLock:
    """Simple file-based lock using fcntl."""
    def __init__(self, filename, timeout=5):
        self.filename = filename
        self.timeout = timeout
        self.fd = None
    
    def __enter__(self):
        self.fd = open(self.filename, 'w')
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            # If we can't get the lock immediately, wait
            start = time.time()
            while time.time() - start < self.timeout:
                try:
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except IOError:
                    time.sleep(0.1)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fd:
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            self.fd.close()
        return False


class GatewayStatsTracker:
    """
    Tracks gateway usage statistics including:
    - Active threads/bots per gateway
    - Total requests per gateway
    - Success/failure rates
    - Response times
    - Concurrent usage tracking
    """
    
    _instance: Optional['GatewayStatsTracker'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'GatewayStatsTracker':
        """Singleton pattern for global stats tracking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._stats_lock = threading.Lock()
        
        # Active threads/tasks per gateway
        self._active_threads: Dict[str, int] = defaultdict(int)
        
        # Request counters per gateway
        self._total_requests: Dict[str, int] = defaultdict(int)
        self._successful_requests: Dict[str, int] = defaultdict(int)
        self._failed_requests: Dict[str, int] = defaultdict(int)
        
        # Response time tracking (last 100 per gateway)
        self._response_times: Dict[str, list] = defaultdict(list)
        self._max_response_times = 100
        
        # Peak concurrent usage
        self._peak_concurrent: Dict[str, int] = defaultdict(int)
        
        # Session start time
        self._session_start = time.time()
        
        # Load persisted stats
        self._load_stats()
        
        self._initialized = True
    
    def _load_stats(self):
        """Load persisted stats from file."""
        try:
            lock = FileLock(GATEWAY_STATS_FILE + '.lock', timeout=5)
            with lock:
                if os.path.exists(GATEWAY_STATS_FILE):
                    with open(GATEWAY_STATS_FILE, 'r') as f:
                        data = json.load(f)
                        # Load historical totals
                        self._total_requests = defaultdict(int, data.get('total_requests', {}))
                        self._successful_requests = defaultdict(int, data.get('successful_requests', {}))
                        self._failed_requests = defaultdict(int, data.get('failed_requests', {}))
                        self._peak_concurrent = defaultdict(int, data.get('peak_concurrent', {}))
        except Exception as e:
            print(f"Warning: Could not load gateway stats: {e}")
    
    def _save_stats(self):
        """Save stats to file for persistence."""
        try:
            lock = FileLock(GATEWAY_STATS_FILE + '.lock', timeout=5)
            with lock:
                data = {
                    'total_requests': dict(self._total_requests),
                    'successful_requests': dict(self._successful_requests),
                    'failed_requests': dict(self._failed_requests),
                    'peak_concurrent': dict(self._peak_concurrent),
                    'last_updated': datetime.now().isoformat()
                }
                with open(GATEWAY_STATS_FILE, 'w') as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save gateway stats: {e}")
    
    def start_request(self, gateway: str) -> None:
        """
        Record the start of a request/thread for a gateway.
        
        Args:
            gateway: Gateway identifier (b3, pp, ppro)
        """
        with self._stats_lock:
            self._active_threads[gateway] += 1
            
            # Update peak concurrent if needed
            if self._active_threads[gateway] > self._peak_concurrent[gateway]:
                self._peak_concurrent[gateway] = self._active_threads[gateway]
    
    def end_request(self, gateway: str, success: bool, response_time: float = 0) -> None:
        """
        Record the end of a request/thread for a gateway.
        
        Args:
            gateway: Gateway identifier (b3, pp, ppro)
            success: Whether the request was successful
            response_time: Time taken for the request in seconds
        """
        with self._stats_lock:
            # Decrement active threads
            self._active_threads[gateway] = max(0, self._active_threads[gateway] - 1)
            
            # Update counters
            self._total_requests[gateway] += 1
            if success:
                self._successful_requests[gateway] += 1
            else:
                self._failed_requests[gateway] += 1
            
            # Track response time
            if response_time > 0:
                self._response_times[gateway].append(response_time)
                # Keep only last N response times
                if len(self._response_times[gateway]) > self._max_response_times:
                    self._response_times[gateway] = self._response_times[gateway][-self._max_response_times:]
            
            # Periodically save stats (every 10 requests)
            total = sum(self._total_requests.values())
            if total % 10 == 0:
                self._save_stats()
    
    def get_active_threads(self, gateway: str = None) -> Dict[str, int]:
        """
        Get active thread count per gateway.
        
        Args:
            gateway: Optional specific gateway, or None for all
            
        Returns:
            Dict of gateway -> active thread count
        """
        with self._stats_lock:
            if gateway:
                return {gateway: self._active_threads.get(gateway, 0)}
            return dict(self._active_threads)
    
    def get_stats(self, gateway: str = None) -> Dict[str, Any]:
        """
        Get comprehensive stats for a gateway or all gateways.
        
        Args:
            gateway: Optional specific gateway, or None for all
            
        Returns:
            Dict with stats
        """
        with self._stats_lock:
            gateways = [gateway] if gateway else ['b3', 'pp', 'ppro']
            
            stats = {}
            for gw in gateways:
                total = self._total_requests.get(gw, 0)
                success = self._successful_requests.get(gw, 0)
                failed = self._failed_requests.get(gw, 0)
                
                # Calculate success rate
                success_rate = (success / total * 100) if total > 0 else 0
                
                # Calculate average response time
                response_times = self._response_times.get(gw, [])
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                
                stats[gw] = {
                    'active_threads': self._active_threads.get(gw, 0),
                    'total_requests': total,
                    'successful_requests': success,
                    'failed_requests': failed,
                    'success_rate': round(success_rate, 2),
                    'avg_response_time': round(avg_response_time, 2),
                    'peak_concurrent': self._peak_concurrent.get(gw, 0),
                }
            
            # Add session info
            uptime = time.time() - self._session_start
            stats['_session'] = {
                'uptime_seconds': round(uptime, 0),
                'uptime_formatted': self._format_uptime(uptime),
                'total_all_gateways': sum(self._total_requests.values()),
            }
            
            return stats
    
    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable format."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def reset_stats(self, gateway: str = None) -> None:
        """
        Reset stats for a gateway or all gateways.
        
        Args:
            gateway: Optional specific gateway, or None for all
        """
        with self._stats_lock:
            if gateway:
                self._total_requests[gateway] = 0
                self._successful_requests[gateway] = 0
                self._failed_requests[gateway] = 0
                self._response_times[gateway] = []
                self._peak_concurrent[gateway] = 0
            else:
                self._total_requests.clear()
                self._successful_requests.clear()
                self._failed_requests.clear()
                self._response_times.clear()
                self._peak_concurrent.clear()
            
            self._save_stats()
    
    def get_formatted_stats(self) -> str:
        """
        Get formatted stats string for display in admin panel.
        
        Returns:
            Formatted string with stats
        """
        stats = self.get_stats()
        
        gateway_names = {
            'b3': 'B3 (Braintree Auth)',
            'pp': 'PP (PPCP)',
            'ppro': 'PPRO (PayPal Pro)'
        }
        
        lines = ["📊 *Gateway Usage Statistics*\n"]
        
        for gw in ['b3', 'pp', 'ppro']:
            gw_stats = stats.get(gw, {})
            name = gateway_names.get(gw, gw.upper())
            
            active = gw_stats.get('active_threads', 0)
            total = gw_stats.get('total_requests', 0)
            success_rate = gw_stats.get('success_rate', 0)
            avg_time = gw_stats.get('avg_response_time', 0)
            peak = gw_stats.get('peak_concurrent', 0)
            
            # Status indicator based on active threads
            if active > 0:
                status = "🟢"
            else:
                status = "⚪"
            
            lines.append(f"{status} *{name}*")
            lines.append(f"   ├ Active: {active} thread(s)")
            lines.append(f"   ├ Total: {total} requests")
            lines.append(f"   ├ Success: {success_rate}%")
            lines.append(f"   ├ Avg Time: {avg_time}s")
            lines.append(f"   └ Peak: {peak} concurrent\n")
        
        # Session info
        session = stats.get('_session', {})
        lines.append(f"⏱️ Session Uptime: {session.get('uptime_formatted', 'N/A')}")
        lines.append(f"📈 Total Requests: {session.get('total_all_gateways', 0)}")
        
        return "\n".join(lines)


# Singleton accessor
def get_gateway_stats() -> GatewayStatsTracker:
    """Get the singleton gateway stats tracker."""
    return GatewayStatsTracker()


# Convenience functions
def track_request_start(gateway: str) -> None:
    """Track the start of a gateway request."""
    get_gateway_stats().start_request(gateway)


def track_request_end(gateway: str, success: bool, response_time: float = 0) -> None:
    """Track the end of a gateway request."""
    get_gateway_stats().end_request(gateway, success, response_time)


def get_active_gateway_threads() -> Dict[str, int]:
    """Get active thread counts for all gateways."""
    return get_gateway_stats().get_active_threads()


def get_gateway_usage_stats() -> Dict[str, Any]:
    """Get comprehensive gateway usage stats."""
    return get_gateway_stats().get_stats()


def get_formatted_gateway_stats() -> str:
    """Get formatted gateway stats for display."""
    return get_gateway_stats().get_formatted_stats()


# Context manager for tracking requests
class GatewayRequestTracker:
    """
    Context manager for tracking gateway requests.
    
    Usage:
        with GatewayRequestTracker('pp') as tracker:
            # Do the request
            result = check_card(...)
            tracker.set_success(result.get('approved', False))
    """
    
    def __init__(self, gateway: str):
        self.gateway = gateway
        self.start_time = None
        self.success = False
    
    def __enter__(self):
        self.start_time = time.time()
        track_request_start(self.gateway)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        response_time = time.time() - self.start_time if self.start_time else 0
        # If exception occurred, mark as failure
        if exc_type is not None:
            self.success = False
        track_request_end(self.gateway, self.success, response_time)
        return False  # Don't suppress exceptions
    
    def set_success(self, success: bool):
        """Set the success status of the request."""
        self.success = success
