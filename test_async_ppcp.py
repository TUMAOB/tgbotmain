#!/usr/bin/env python3
"""
Test script for async PPCP checker
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ppcp.async_ppcpgatewaycvv import check_multiple_cards

async def test_async_checker():
    """Test async checker with sample data"""
    # Sample test data
    sites = [
        "https://aquarestoutlet.com",
        "https://graysfitness.com.au"
    ]
    
    # Test cards (these are fake/test cards)
    cards = [
        "4111111111111111|12|25|123",
        "4242424242424242|11|26|456"
    ]
    
    print("Testing async PPCP checker...")
    print(f"Testing {len(cards)} cards on {len(sites)} sites")
    
    try:
        results = await check_multiple_cards(cards, sites, max_concurrent=2)
        for i, result in enumerate(results):
            print(f"\nResult {i+1}:")
            print(result)
    except Exception as e:
        print(f"Test failed: {e}")
        return False
    
    print("\nTest completed successfully!")
    return True

if __name__ == "__main__":
    asyncio.run(test_async_checker())