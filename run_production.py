#!/usr/bin/env python3
"""
Production runner for async PPCP checker
"""
import asyncio
import os
import sys
import logging
from ppcp.async_ppcpgatewaycvv import main_async

# Load environment variables if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Set up logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv('LOG_FILE', 'ppcp_checker.log')),
        logging.StreamHandler()
    ]
)

def main():
    """Main entry point"""
    print("Starting PPCP Checker in production mode...")
    print(f"Max concurrent requests: {os.getenv('MAX_CONCURRENT_REQUESTS', '100')}")
    print(f"Rate limit per second: {os.getenv('RATE_LIMIT_PER_SECOND', '10')}")
    
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()