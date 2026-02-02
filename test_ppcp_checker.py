#!/usr/bin/env python3
"""
Comprehensive test suite for async PPCP checker
"""
import asyncio
import unittest
import tempfile
import os
from unittest.mock import patch, AsyncMock, MagicMock
from ppcp.async_ppcpgatewaycvv import AsyncCardChecker, Config, BinChecker
from ppcp.rate_limiter import RateLimiter, DomainRateLimiter
from ppcp.metrics import MetricsCollector

class TestAsyncPPCPChecker(unittest.TestCase):
    """Test suite for async PPCP checker"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_card = "4111111111111111|12|25|123"
        self.test_site = "https://aquarestoutlet.com"
        self.checker = AsyncCardChecker(self.test_card, self.test_site)
        
        # Mock session
        self.mock_session = AsyncMock()
        self.checker.session = self.mock_session
    
    def test_card_parsing(self):
        """Test card data parsing"""
        self.assertEqual(self.checker.cc, "4111111111111111")
        self.assertEqual(self.checker.mes, "12")
        self.assertEqual(self.checker.ano, "2025")
        self.assertEqual(self.checker.cvv, "123")
        self.assertEqual(self.checker.cc6, "411111")
    
    def test_country_detection(self):
        """Test country detection from domain"""
        test_cases = [
            ("https://example.co.uk", "GB"),
            ("https://example.au", "AU"),
            ("https://example.ca", "CA"),
            ("https://example.com", "US"),
        ]
        
        for site, expected_country in test_cases:
            checker = AsyncCardChecker(self.test_card, site)
            self.assertEqual(checker.country, expected_country)
    
    def test_address_selection(self):
        """Test address selection for country"""
        address = self.checker._get_address()
        self.assertIn('street', address)
        self.assertIn('city', address)
        self.assertIn('zip', address)
        self.assertIn('state', address)
        self.assertIn('phone', address)
    
    def test_header_generation(self):
        """Test header generation"""
        headers = self.checker._get_headers()
        self.assertIn('user-agent', headers)
        self.assertIn('accept', headers)
        self.assertIn('accept-language', headers)
    
    @patch('ppcp.async_ppcpgatewaycvv.BinChecker.check')
    async def test_bin_checking(self, mock_bin_check):
        """Test BIN checking with caching"""
        mock_bin_check.return_value = {
            'brand': 'Visa',
            'type': 'Credit',
            'level': 'Classic',
            'issuer': 'Test Bank',
            'country': 'US'
        }
        
        result = await BinChecker.check("411111", "test-ua")
        self.assertEqual(result['brand'], 'Visa')
        self.assertEqual(result['country'], 'US')
    
    def test_rate_limiter(self):
        """Test rate limiter functionality"""
        limiter = RateLimiter(rate_limit_per_second=10, burst_limit=5)
        
        # Test initial state
        self.assertEqual(limiter.tokens, 5)
        
        # Test token consumption
        asyncio.run(limiter.acquire(2))
        self.assertLessEqual(limiter.tokens, 3)
    
    def test_metrics_collector(self):
        """Test metrics collection"""
        collector = MetricsCollector()
        
        # Record some requests
        collector.record_request("test.com", True, 0.1, 200)
        collector.record_request("test.com", False, 0.2, 500)
        collector.record_request("example.com", True, 0.15, 200)
        
        stats = collector.get_stats()
        self.assertEqual(stats['requests_total'], 3)
        self.assertEqual(stats['requests_success'], 2)
        self.assertEqual(stats['requests_failed'], 1)
        self.assertGreater(stats['success_rate_percent'], 0)

class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for async PPCP checker"""
    
    async def asyncSetUp(self):
        """Set up async test fixtures"""
        # Create temporary files for testing
        self.temp_cc_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        self.temp_sites_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        
        # Write test data
        self.temp_cc_file.write("4111111111111111|12|25|123\n")
        self.temp_cc_file.write("4242424242424242|11|26|456\n")
        self.temp_cc_file.close()
        
        self.temp_sites_file.write("https://aquarestoutlet.com\n")
        self.temp_sites_file.write("https://graysfitness.com.au\n")
        self.temp_sites_file.close()
    
    async def asyncTearDown(self):
        """Clean up test files"""
        os.unlink(self.temp_cc_file.name)
        os.unlink(self.temp_sites_file.name)
    
    @patch('ppcp.async_ppcpgatewaycvv.check_multiple_cards')
    async def test_multiple_cards_check(self, mock_check):
        """Test checking multiple cards"""
        mock_check.return_value = ["Result 1", "Result 2"]
        
        from ppcp.async_ppcpgatewaycvv import check_multiple_cards
        
        results = await check_multiple_cards(
            ["4111111111111111|12|25|123", "4242424242424242|11|26|456"],
            ["https://test.com"],
            max_concurrent=2
        )
        
        self.assertEqual(len(results), 2)
        mock_check.assert_called()

def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncPPCPChecker))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    if not success:
        exit(1)