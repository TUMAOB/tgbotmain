#!/usr/bin/env python3
"""
Production runner for async PPCP checker - Optimized for high performance
Features:
- Configurable concurrency and rate limiting
- Memory-efficient connection pooling
- Graceful shutdown handling
- Health monitoring and metrics
- Environment-based configuration
"""
import asyncio
import os
import sys
import logging
import signal
import gc
from typing import Optional

# Load environment variables if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Production Configuration
class ProductionConfig:
    """Production configuration with environment variable support"""
    
    # Request settings - optimized for speed
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '15'))
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '50'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '2'))
    RETRY_DELAY = float(os.getenv('RETRY_DELAY', '0.5'))
    
    # Rate limiting - balanced for performance
    RATE_LIMIT_PER_SECOND = int(os.getenv('RATE_LIMIT_PER_SECOND', '20'))
    
    # Connection pooling - optimized for production
    CONNECTION_LIMIT = int(os.getenv('CONNECTION_LIMIT', '100'))
    CONNECTION_LIMIT_PER_HOST = int(os.getenv('CONNECTION_LIMIT_PER_HOST', '20'))
    DNS_CACHE_TTL = int(os.getenv('DNS_CACHE_TTL', '600'))
    KEEPALIVE_TIMEOUT = int(os.getenv('KEEPALIVE_TIMEOUT', '30'))
    
    # BIN lookup settings
    BIN_CHECK_TIMEOUT = int(os.getenv('BIN_CHECK_TIMEOUT', '5'))
    BIN_CACHE_SIZE = int(os.getenv('BIN_CACHE_SIZE', '1000'))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'ppcp_checker.log')
    LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Memory management
    GC_THRESHOLD = int(os.getenv('GC_THRESHOLD', '1000'))  # Run GC every N requests
    
    # Telegram notifications
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    @classmethod
    def print_config(cls):
        """Print current configuration"""
        print("=" * 50)
        print("Production Configuration:")
        print("=" * 50)
        print(f"  Request Timeout: {cls.REQUEST_TIMEOUT}s")
        print(f"  Max Concurrent Requests: {cls.MAX_CONCURRENT_REQUESTS}")
        print(f"  Max Retries: {cls.MAX_RETRIES}")
        print(f"  Retry Delay: {cls.RETRY_DELAY}s")
        print(f"  Rate Limit: {cls.RATE_LIMIT_PER_SECOND}/s")
        print(f"  Connection Limit: {cls.CONNECTION_LIMIT}")
        print(f"  Connection Limit Per Host: {cls.CONNECTION_LIMIT_PER_HOST}")
        print(f"  DNS Cache TTL: {cls.DNS_CACHE_TTL}s")
        print(f"  BIN Check Timeout: {cls.BIN_CHECK_TIMEOUT}s")
        print(f"  Log Level: {cls.LOG_LEVEL}")
        print("=" * 50)


# Set up logging
def setup_logging():
    """Configure production logging"""
    log_level = getattr(logging, ProductionConfig.LOG_LEVEL.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(ProductionConfig.LOG_FORMAT)
    
    # File handler with rotation
    file_handler = logging.FileHandler(ProductionConfig.LOG_FILE)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)


# Global shutdown flag
shutdown_event: Optional[asyncio.Event] = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"\n⚠️ Received signal {signum}, initiating graceful shutdown...")
    if shutdown_event:
        shutdown_event.set()


async def run_health_check(logger):
    """Periodic health check and memory management"""
    request_count = 0
    
    while not shutdown_event.is_set():
        try:
            await asyncio.sleep(60)  # Check every minute
            
            # Log memory usage
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            logger.info(f"Health check - Memory usage: {memory_mb:.2f} MB")
            
            # Run garbage collection periodically
            request_count += 1
            if request_count >= ProductionConfig.GC_THRESHOLD:
                gc.collect()
                request_count = 0
                logger.debug("Garbage collection completed")
                
        except ImportError:
            # psutil not available, skip memory logging
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Health check error: {e}")


async def main_async():
    """Async main function for production use"""
    global shutdown_event
    shutdown_event = asyncio.Event()
    
    logger = setup_logging()
    
    # Print configuration
    ProductionConfig.print_config()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting PPCP Checker in production mode...")
    
    try:
        # Import the main async module
        from ppcp.async_ppcpgatewaycvv import main_async as ppcp_main
        
        # Start health check task
        health_task = asyncio.create_task(run_health_check(logger))
        
        # Run the main checker
        await ppcp_main()
        
        # Cancel health check on completion
        health_task.cancel()
        try:
            await health_task
        except asyncio.CancelledError:
            pass
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("Shutdown complete")


def main():
    """Main entry point"""
    print("🚀 Starting PPCP Checker in production mode...")
    
    try:
        # Use uvloop for better performance if available
        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            print("✅ Using uvloop for enhanced performance")
        except ImportError:
            print("ℹ️ uvloop not available, using default event loop")
        
        asyncio.run(main_async())
        
    except KeyboardInterrupt:
        print("\n⚠️ Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
