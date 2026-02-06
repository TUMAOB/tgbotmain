#!/usr/bin/env python3
"""
High-Concurrency Request Manager for Card Checking Bot
Optimized for bare metal servers handling hundreds of simultaneous users.

Features:
- Per-gateway request queues with configurable concurrency
- Non-blocking request processing
- Automatic load balancing across gateways
- Request prioritization (admin requests get priority)
- Real-time statistics tracking
- Memory-efficient queue management
"""

import asyncio
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RequestPriority(Enum):
    """Request priority levels."""
    HIGH = 0      # Admin requests
    NORMAL = 1    # Regular user single checks
    LOW = 2       # Mass check requests


@dataclass
class GatewayConfig:
    """Configuration for a specific gateway."""
    name: str
    max_concurrent: int = 100  # Maximum concurrent requests for this gateway
    rate_limit_per_second: float = 50.0  # Requests per second
    burst_capacity: int = 100  # Burst capacity
    timeout: float = 30.0  # Request timeout in seconds
    retry_count: int = 2  # Number of retries on failure


@dataclass
class RequestItem:
    """A single request in the queue."""
    id: str
    user_id: int
    gateway: str
    card_data: str
    callback: Optional[Callable] = None
    priority: RequestPriority = RequestPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    is_admin: bool = False
    extra_data: Dict = field(default_factory=dict)
    
    def __lt__(self, other):
        """Compare by priority for priority queue."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class GatewayStats:
    """Real-time statistics for a gateway."""
    
    def __init__(self, gateway_name: str):
        self.gateway_name = gateway_name
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.active_requests = 0
        self.queue_size = 0
        self.total_response_time = 0.0
        self.last_request_time = 0.0
        self._lock = threading.Lock()
    
    def record_start(self):
        """Record request start."""
        with self._lock:
            self.active_requests += 1
            self.total_requests += 1
            self.last_request_time = time.time()
    
    def record_end(self, success: bool, response_time: float):
        """Record request end."""
        with self._lock:
            self.active_requests = max(0, self.active_requests - 1)
            self.total_response_time += response_time
            if success:
                self.successful_requests += 1
            else:
                self.failed_requests += 1
    
    def update_queue_size(self, size: int):
        """Update queue size."""
        with self._lock:
            self.queue_size = size
    
    def get_stats(self) -> Dict:
        """Get current statistics."""
        with self._lock:
            avg_response = (
                self.total_response_time / self.total_requests 
                if self.total_requests > 0 else 0
            )
            return {
                'gateway': self.gateway_name,
                'total_requests': self.total_requests,
                'successful': self.successful_requests,
                'failed': self.failed_requests,
                'active': self.active_requests,
                'queue_size': self.queue_size,
                'avg_response_time': round(avg_response, 3),
                'success_rate': round(
                    self.successful_requests / self.total_requests * 100, 2
                ) if self.total_requests > 0 else 0
            }


class GatewayRequestQueue:
    """
    High-performance request queue for a single gateway.
    Uses asyncio.PriorityQueue for efficient request ordering.
    """
    
    def __init__(self, config: GatewayConfig):
        self.config = config
        self.queue: asyncio.PriorityQueue = None
        self.semaphore: asyncio.Semaphore = None
        self.stats = GatewayStats(config.name)
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._check_function: Optional[Callable] = None
    
    async def initialize(self):
        """Initialize the queue and semaphore."""
        self.queue = asyncio.PriorityQueue()
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._running = True
    
    def set_check_function(self, func: Callable):
        """Set the function to call for checking cards."""
        self._check_function = func
    
    async def enqueue(self, request: RequestItem) -> bool:
        """
        Add a request to the queue.
        Returns True if successfully queued.
        """
        if not self._running:
            return False
        
        await self.queue.put((request.priority.value, request.created_at, request))
        self.stats.update_queue_size(self.queue.qsize())
        return True
    
    async def process_request(self, request: RequestItem) -> Tuple[bool, Any]:
        """Process a single request with semaphore control."""
        async with self.semaphore:
            self.stats.record_start()
            start_time = time.time()
            
            try:
                if self._check_function:
                    result = await self._check_function(request)
                    elapsed = time.time() - start_time
                    self.stats.record_end(True, elapsed)
                    return True, result
                else:
                    elapsed = time.time() - start_time
                    self.stats.record_end(False, elapsed)
                    return False, "No check function configured"
            except Exception as e:
                elapsed = time.time() - start_time
                self.stats.record_end(False, elapsed)
                logger.error(f"Error processing request: {e}")
                return False, str(e)
    
    async def worker(self, worker_id: int):
        """Worker coroutine that processes requests from the queue."""
        while self._running:
            try:
                # Get request with timeout to allow graceful shutdown
                try:
                    priority, created_at, request = await asyncio.wait_for(
                        self.queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                self.stats.update_queue_size(self.queue.qsize())
                
                # Process the request
                success, result = await self.process_request(request)
                
                # Call callback if provided
                if request.callback:
                    try:
                        if asyncio.iscoroutinefunction(request.callback):
                            await request.callback(request, success, result)
                        else:
                            request.callback(request, success, result)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                
                self.queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
    
    async def start_workers(self, num_workers: int = None):
        """Start worker coroutines."""
        if num_workers is None:
            num_workers = self.config.max_concurrent
        
        for i in range(num_workers):
            task = asyncio.create_task(self.worker(i))
            self._workers.append(task)
    
    async def stop(self):
        """Stop all workers gracefully."""
        self._running = False
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
    
    def get_stats(self) -> Dict:
        """Get queue statistics."""
        return self.stats.get_stats()


class ConcurrencyManager:
    """
    Central manager for all gateway request queues.
    Handles routing, load balancing, and statistics.
    """
    
    # Default configurations for each gateway (optimized for bare metal)
    DEFAULT_CONFIGS = {
        'b3': GatewayConfig(
            name='b3',
            max_concurrent=150,  # Braintree Auth
            rate_limit_per_second=100.0,
            burst_capacity=200,
            timeout=30.0
        ),
        'pp': GatewayConfig(
            name='pp',
            max_concurrent=150,  # PPCP
            rate_limit_per_second=100.0,
            burst_capacity=200,
            timeout=30.0
        ),
        'ppro': GatewayConfig(
            name='ppro',
            max_concurrent=150,  # PayPal Pro
            rate_limit_per_second=100.0,
            burst_capacity=200,
            timeout=30.0
        ),
        'st': GatewayConfig(
            name='st',
            max_concurrent=150,  # Stripe
            rate_limit_per_second=100.0,
            burst_capacity=200,
            timeout=30.0
        ),
    }
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for global access."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.queues: Dict[str, GatewayRequestQueue] = {}
        self.configs = self.DEFAULT_CONFIGS.copy()
        self._running = False
        self._initialized = True
        self._request_counter = 0
        self._counter_lock = threading.Lock()
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        with self._counter_lock:
            self._request_counter += 1
            return f"req_{int(time.time())}_{self._request_counter}"
    
    async def initialize(self, custom_configs: Dict[str, GatewayConfig] = None):
        """Initialize all gateway queues."""
        if custom_configs:
            self.configs.update(custom_configs)
        
        for gateway_name, config in self.configs.items():
            queue = GatewayRequestQueue(config)
            await queue.initialize()
            self.queues[gateway_name] = queue
        
        self._running = True
        logger.info(f"ConcurrencyManager initialized with {len(self.queues)} gateways")
    
    async def start(self):
        """Start all gateway workers."""
        for gateway_name, queue in self.queues.items():
            await queue.start_workers()
            logger.info(f"Started workers for gateway: {gateway_name}")
    
    async def stop(self):
        """Stop all gateway workers."""
        self._running = False
        for queue in self.queues.values():
            await queue.stop()
        logger.info("ConcurrencyManager stopped")
    
    def set_check_function(self, gateway: str, func: Callable):
        """Set the check function for a gateway."""
        if gateway in self.queues:
            self.queues[gateway].set_check_function(func)
    
    async def submit_request(
        self,
        gateway: str,
        user_id: int,
        card_data: str,
        callback: Optional[Callable] = None,
        is_admin: bool = False,
        extra_data: Dict = None
    ) -> Optional[str]:
        """
        Submit a card check request to the appropriate gateway queue.
        
        Args:
            gateway: Gateway name (b3, pp, ppro, st)
            user_id: Telegram user ID
            card_data: Card data string
            callback: Optional callback function(request, success, result)
            is_admin: Whether the user is admin
            extra_data: Additional data to pass through
            
        Returns:
            Request ID if queued successfully, None otherwise
        """
        if gateway not in self.queues:
            logger.error(f"Unknown gateway: {gateway}")
            return None
        
        request = RequestItem(
            id=self._generate_request_id(),
            user_id=user_id,
            gateway=gateway,
            card_data=card_data,
            callback=callback,
            priority=RequestPriority.HIGH if is_admin else RequestPriority.NORMAL,
            is_admin=is_admin,
            extra_data=extra_data or {}
        )
        
        success = await self.queues[gateway].enqueue(request)
        return request.id if success else None
    
    async def submit_batch(
        self,
        gateway: str,
        user_id: int,
        cards: List[str],
        callback: Optional[Callable] = None,
        is_admin: bool = False
    ) -> List[str]:
        """
        Submit multiple card check requests.
        
        Returns:
            List of request IDs
        """
        request_ids = []
        for card in cards:
            req_id = await self.submit_request(
                gateway=gateway,
                user_id=user_id,
                card_data=card,
                callback=callback,
                is_admin=is_admin
            )
            if req_id:
                request_ids.append(req_id)
        return request_ids
    
    def get_gateway_stats(self, gateway: str) -> Optional[Dict]:
        """Get statistics for a specific gateway."""
        if gateway in self.queues:
            return self.queues[gateway].get_stats()
        return None
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all gateways."""
        return {
            gateway: queue.get_stats() 
            for gateway, queue in self.queues.items()
        }
    
    def get_total_active_requests(self) -> int:
        """Get total number of active requests across all gateways."""
        return sum(
            queue.stats.active_requests 
            for queue in self.queues.values()
        )
    
    def get_total_queue_size(self) -> int:
        """Get total queue size across all gateways."""
        return sum(
            queue.stats.queue_size 
            for queue in self.queues.values()
        )
    
    def update_gateway_config(self, gateway: str, **kwargs):
        """Update gateway configuration dynamically."""
        if gateway in self.configs:
            config = self.configs[gateway]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            # Update semaphore if max_concurrent changed
            if 'max_concurrent' in kwargs and gateway in self.queues:
                self.queues[gateway].semaphore = asyncio.Semaphore(kwargs['max_concurrent'])


# Global instance
concurrency_manager = ConcurrencyManager()


async def get_concurrency_manager() -> ConcurrencyManager:
    """Get the global concurrency manager instance."""
    if not concurrency_manager._running:
        await concurrency_manager.initialize()
        await concurrency_manager.start()
    return concurrency_manager


# Helper functions for easy integration
async def submit_card_check(
    gateway: str,
    user_id: int,
    card_data: str,
    callback: Optional[Callable] = None,
    is_admin: bool = False
) -> Optional[str]:
    """
    Convenience function to submit a card check request.
    
    Example:
        request_id = await submit_card_check('b3', user_id, '4111111111111111|12|25|123')
    """
    manager = await get_concurrency_manager()
    return await manager.submit_request(
        gateway=gateway,
        user_id=user_id,
        card_data=card_data,
        callback=callback,
        is_admin=is_admin
    )


def get_system_stats() -> Dict:
    """Get overall system statistics."""
    return {
        'gateways': concurrency_manager.get_all_stats(),
        'total_active': concurrency_manager.get_total_active_requests(),
        'total_queued': concurrency_manager.get_total_queue_size()
    }
