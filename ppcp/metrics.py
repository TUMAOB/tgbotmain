#!/usr/bin/env python3
"""
Health monitoring and metrics for PPCP checker
"""
import asyncio
import time
from typing import Dict, Any
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collect and track performance metrics"""
    
    def __init__(self):
        self.requests_total = 0
        self.requests_success = 0
        self.requests_failed = 0
        self.response_times = deque(maxlen=1000)  # Keep last 1000 response times
        self.domain_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0})
        self.status_codes = defaultdict(int)
        self.start_time = time.time()
    
    def record_request(self, domain: str, success: bool, response_time: float, status_code: int = 0):
        """Record a request metric"""
        self.requests_total += 1
        if success:
            self.requests_success += 1
        else:
            self.requests_failed += 1
        
        self.response_times.append(response_time)
        self.domain_stats[domain]['total'] += 1
        if success:
            self.domain_stats[domain]['success'] += 1
        else:
            self.domain_stats[domain]['failed'] += 1
        
        if status_code > 0:
            self.status_codes[status_code] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        uptime = time.time() - self.start_time
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        
        success_rate = (self.requests_success / self.requests_total * 100) if self.requests_total > 0 else 0
        
        return {
            'uptime_seconds': uptime,
            'requests_total': self.requests_total,
            'requests_success': self.requests_success,
            'requests_failed': self.requests_failed,
            'success_rate_percent': success_rate,
            'average_response_time': avg_response_time,
            'requests_per_second': self.requests_total / uptime if uptime > 0 else 0,
            'domain_stats': dict(self.domain_stats),
            'status_codes': dict(self.status_codes)
        }
    
    def log_stats(self):
        """Log current statistics"""
        stats = self.get_stats()
        logger.info(f"Metrics - Total: {stats['requests_total']}, "
                   f"Success: {stats['requests_success']}, "
                   f"Failed: {stats['requests_failed']}, "
                   f"Success Rate: {stats['success_rate_percent']:.2f}%, "
                   f"Avg Response Time: {stats['average_response_time']:.2f}s")

# Global metrics collector
metrics_collector = MetricsCollector()