#!/usr/bin/env python3
"""
Standalone test script to verify restart functionality.
This test doesn't require external dependencies - it tests the logic directly.
"""

import os
import sys
import json
import tempfile
import shutil
import unittest
from datetime import datetime


# ============= EXTRACTED RESTART LOGIC FOR TESTING =============
# These are copies of the functions from auth.py for standalone testing

RESTART_STATE_FILE = 'test_restart_state.json'
RESTART_STATE_LOCK_FILE = 'test_restart_state.json.lock'

# Restart error codes
RESTART_ERROR_NONE = 0
RESTART_ERROR_SCRIPT_NOT_FOUND = 1
RESTART_ERROR_DEPENDENCIES_MISSING = 2
RESTART_ERROR_STATE_SAVE_FAILED = 3
RESTART_ERROR_PROCESS_START_FAILED = 4
RESTART_ERROR_VALIDATION_FAILED = 5


class RestartError(Exception):
    """Custom exception for restart-related errors"""
    def __init__(self, message: str, error_code: int):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


def validate_restart_prerequisites_standalone(script_path=None, check_modules=False):
    """
    Validate that all prerequisites for restart are met.
    Standalone version for testing.
    
    Returns:
        Tuple of (is_valid: bool, error_message: str, error_code: int)
    """
    if script_path is None:
        script_path = os.path.abspath(__file__)
    
    # Check 1: Verify the script file exists
    if not os.path.exists(script_path):
        return False, f"Script file not found: {script_path}", RESTART_ERROR_SCRIPT_NOT_FOUND
    
    # Check 2: Verify the script is readable
    if not os.access(script_path, os.R_OK):
        return False, f"Script file not readable: {script_path}", RESTART_ERROR_SCRIPT_NOT_FOUND
    
    # Check 3: Verify Python executable exists
    if not os.path.exists(sys.executable):
        return False, f"Python executable not found: {sys.executable}", RESTART_ERROR_DEPENDENCIES_MISSING
    
    # Check 4: Verify critical dependencies are importable (optional)
    if check_modules:
        critical_modules = [
            ('json', 'json'),
            ('os', 'os'),
            ('sys', 'sys'),
        ]
        
        missing_modules = []
        for module_name, package_name in critical_modules:
            try:
                __import__(module_name)
            except ImportError:
                missing_modules.append(package_name)
        
        if missing_modules:
            return False, f"Missing dependencies: {', '.join(missing_modules)}", RESTART_ERROR_DEPENDENCIES_MISSING
    
    return True, "All prerequisites validated", RESTART_ERROR_NONE


def save_restart_state_standalone(updated_files=None, show_admin_menu=False, admin_id=12345):
    """
    Save restart state to notify admin after restart.
    Standalone version for testing.
    
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    try:
        state = {
            'pending_notification': True,
            'admin_id': admin_id,
            'updated_files': updated_files or [],
            'restart_time': datetime.now().isoformat(),
            'show_admin_menu': show_admin_menu
        }
        with open(RESTART_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        return True, "State saved successfully"
    except Exception as e:
        return False, f"Failed to save restart state: {str(e)}"


def load_restart_state_standalone():
    """Load restart state from file. Standalone version for testing."""
    try:
        if os.path.exists(RESTART_STATE_FILE):
            try:
                with open(RESTART_STATE_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                print(f"⚠️ Restart state file corrupted: {str(e)}")
                return None
            except Exception as e:
                print(f"⚠️ Error reading restart state: {str(e)}")
                return None
        return None
    except Exception as e:
        print(f"⚠️ Failed to read restart state: {str(e)}")
        return None


def clear_restart_state_standalone():
    """Clear restart state after notification is sent. Standalone version for testing."""
    try:
        if os.path.exists(RESTART_STATE_FILE):
            os.remove(RESTART_STATE_FILE)
    except Exception as e:
        print(f"⚠️ Failed to clear restart state: {str(e)}")


# ============= TEST CLASSES =============

class TestRestartPrerequisites(unittest.TestCase):
    """Test the validate_restart_prerequisites function"""
    
    def test_valid_prerequisites(self):
        """Test that validation passes with all prerequisites met"""
        is_valid, message, error_code = validate_restart_prerequisites_standalone()
        self.assertTrue(is_valid, f"Validation should pass: {message}")
        self.assertEqual(error_code, RESTART_ERROR_NONE)
    
    def test_missing_script_file(self):
        """Test validation fails when script file doesn't exist"""
        is_valid, message, error_code = validate_restart_prerequisites_standalone(
            script_path='/nonexistent/path/to/script.py'
        )
        self.assertFalse(is_valid)
        self.assertEqual(error_code, RESTART_ERROR_SCRIPT_NOT_FOUND)
        self.assertIn('not found', message.lower())
    
    def test_unreadable_script_file(self):
        """Test validation fails when script file is not readable"""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# test script")
            temp_path = f.name
        
        try:
            # Make it unreadable (if possible)
            try:
                os.chmod(temp_path, 0o000)
                is_valid, message, error_code = validate_restart_prerequisites_standalone(
                    script_path=temp_path
                )
                # On some systems this might still be readable by root
                if not is_valid:
                    self.assertEqual(error_code, RESTART_ERROR_SCRIPT_NOT_FOUND)
            except PermissionError:
                # Can't change permissions, skip this test
                pass
        finally:
            # Restore permissions and clean up
            try:
                os.chmod(temp_path, 0o644)
            except:
                pass
            os.unlink(temp_path)
    
    def test_module_check_passes(self):
        """Test that module check passes for standard library modules"""
        is_valid, message, error_code = validate_restart_prerequisites_standalone(
            check_modules=True
        )
        self.assertTrue(is_valid)
        self.assertEqual(error_code, RESTART_ERROR_NONE)


class TestRestartState(unittest.TestCase):
    """Test restart state save/load/clear functions"""
    
    def setUp(self):
        """Clean up any existing state files"""
        for f in [RESTART_STATE_FILE, RESTART_STATE_LOCK_FILE]:
            if os.path.exists(f):
                os.remove(f)
    
    def tearDown(self):
        """Clean up after tests"""
        for f in [RESTART_STATE_FILE, RESTART_STATE_LOCK_FILE]:
            if os.path.exists(f):
                os.remove(f)
    
    def test_save_and_load_state(self):
        """Test saving and loading restart state"""
        updated_files = ['auth.py', 'system_manager.py']
        
        # Save state
        success, message = save_restart_state_standalone(
            updated_files=updated_files,
            show_admin_menu=True
        )
        self.assertTrue(success, f"Save should succeed: {message}")
        
        # Load state
        state = load_restart_state_standalone()
        self.assertIsNotNone(state)
        self.assertTrue(state.get('pending_notification'))
        self.assertEqual(state.get('updated_files'), updated_files)
        self.assertTrue(state.get('show_admin_menu'))
        self.assertIn('restart_time', state)
    
    def test_save_state_with_empty_files(self):
        """Test saving state with no updated files"""
        success, message = save_restart_state_standalone(
            updated_files=None,
            show_admin_menu=False
        )
        self.assertTrue(success)
        
        state = load_restart_state_standalone()
        self.assertIsNotNone(state)
        self.assertEqual(state.get('updated_files'), [])
        self.assertFalse(state.get('show_admin_menu'))
    
    def test_clear_state(self):
        """Test clearing restart state"""
        # First save some state
        save_restart_state_standalone(updated_files=['test.py'], show_admin_menu=True)
        
        # Verify it exists
        self.assertTrue(os.path.exists(RESTART_STATE_FILE))
        
        # Clear it
        clear_restart_state_standalone()
        
        # Verify it's gone
        self.assertFalse(os.path.exists(RESTART_STATE_FILE))
    
    def test_load_nonexistent_state(self):
        """Test loading state when file doesn't exist"""
        # Ensure file doesn't exist
        if os.path.exists(RESTART_STATE_FILE):
            os.remove(RESTART_STATE_FILE)
        
        state = load_restart_state_standalone()
        self.assertIsNone(state)
    
    def test_load_corrupted_state(self):
        """Test loading corrupted state file"""
        # Write invalid JSON
        with open(RESTART_STATE_FILE, 'w') as f:
            f.write('not valid json {{{')
        
        state = load_restart_state_standalone()
        self.assertIsNone(state)
    
    def test_clear_nonexistent_state(self):
        """Test clearing state when file doesn't exist (should not raise)"""
        # Ensure file doesn't exist
        if os.path.exists(RESTART_STATE_FILE):
            os.remove(RESTART_STATE_FILE)
        
        # Should not raise
        clear_restart_state_standalone()
    
    def test_state_contains_timestamp(self):
        """Test that saved state contains a valid timestamp"""
        save_restart_state_standalone(updated_files=['test.py'])
        
        state = load_restart_state_standalone()
        self.assertIn('restart_time', state)
        
        # Verify it's a valid ISO format timestamp
        try:
            datetime.fromisoformat(state['restart_time'])
        except ValueError:
            self.fail("restart_time should be a valid ISO format timestamp")
    
    def test_state_contains_admin_id(self):
        """Test that saved state contains admin ID"""
        admin_id = 7405188060
        save_restart_state_standalone(updated_files=['test.py'], admin_id=admin_id)
        
        state = load_restart_state_standalone()
        self.assertEqual(state.get('admin_id'), admin_id)


class TestRestartErrorCodes(unittest.TestCase):
    """Test that error codes are properly defined and used"""
    
    def test_error_codes_exist(self):
        """Test that all error codes are defined"""
        # Verify they are integers
        self.assertIsInstance(RESTART_ERROR_NONE, int)
        self.assertIsInstance(RESTART_ERROR_SCRIPT_NOT_FOUND, int)
        self.assertIsInstance(RESTART_ERROR_DEPENDENCIES_MISSING, int)
        self.assertIsInstance(RESTART_ERROR_STATE_SAVE_FAILED, int)
        self.assertIsInstance(RESTART_ERROR_PROCESS_START_FAILED, int)
        self.assertIsInstance(RESTART_ERROR_VALIDATION_FAILED, int)
        
        # Verify they are unique
        codes = [
            RESTART_ERROR_NONE,
            RESTART_ERROR_SCRIPT_NOT_FOUND,
            RESTART_ERROR_DEPENDENCIES_MISSING,
            RESTART_ERROR_STATE_SAVE_FAILED,
            RESTART_ERROR_PROCESS_START_FAILED,
            RESTART_ERROR_VALIDATION_FAILED
        ]
        self.assertEqual(len(codes), len(set(codes)), "Error codes should be unique")
    
    def test_restart_error_exception(self):
        """Test the RestartError exception class"""
        error = RestartError("Test error message", 42)
        self.assertEqual(error.message, "Test error message")
        self.assertEqual(error.error_code, 42)
        self.assertEqual(str(error), "Test error message")
    
    def test_restart_error_can_be_raised(self):
        """Test that RestartError can be raised and caught"""
        with self.assertRaises(RestartError) as context:
            raise RestartError("Test error", RESTART_ERROR_VALIDATION_FAILED)
        
        self.assertEqual(context.exception.error_code, RESTART_ERROR_VALIDATION_FAILED)


class TestEntryPointValidation(unittest.TestCase):
    """Test that auth.py is the correct entry point"""
    
    def test_auth_py_exists(self):
        """Test that auth.py exists"""
        self.assertTrue(os.path.exists('auth.py'), "auth.py should exist")
    
    def test_script_can_be_run_directly(self):
        """Test that auth.py has proper __main__ block"""
        with open('auth.py', 'r') as f:
            content = f.read()
        
        self.assertIn("if __name__ == '__main__':", content)
        self.assertIn("main()", content)
    
    def test_required_handlers_registered(self):
        """Test that main() registers required handlers"""
        with open('auth.py', 'r') as f:
            content = f.read()
        
        # Check for essential command handlers
        required_handlers = [
            'CommandHandler("start"',
            'CommandHandler("admin"',
            'CommandHandler("b3"',
        ]
        
        for handler in required_handlers:
            self.assertIn(handler, content, f"Handler {handler} should be registered")
    
    def test_restart_functions_exist(self):
        """Test that restart functions are defined in auth.py"""
        with open('auth.py', 'r') as f:
            content = f.read()
        
        required_functions = [
            'def validate_restart_prerequisites',
            'def save_restart_state',
            'def load_restart_state',
            'def clear_restart_state',
            'def auto_restart_bot',
        ]
        
        for func in required_functions:
            self.assertIn(func, content, f"Function {func} should be defined")
    
    def test_error_codes_defined(self):
        """Test that error codes are defined in auth.py"""
        with open('auth.py', 'r') as f:
            content = f.read()
        
        required_codes = [
            'RESTART_ERROR_NONE',
            'RESTART_ERROR_SCRIPT_NOT_FOUND',
            'RESTART_ERROR_DEPENDENCIES_MISSING',
            'RESTART_ERROR_STATE_SAVE_FAILED',
            'RESTART_ERROR_PROCESS_START_FAILED',
            'RESTART_ERROR_VALIDATION_FAILED',
        ]
        
        for code in required_codes:
            self.assertIn(code, content, f"Error code {code} should be defined")
    
    def test_restart_error_class_defined(self):
        """Test that RestartError class is defined in auth.py"""
        with open('auth.py', 'r') as f:
            content = f.read()
        
        self.assertIn('class RestartError', content)


class TestErrorHandling(unittest.TestCase):
    """Test error handling in restart logic"""
    
    def setUp(self):
        """Clean up any existing state files"""
        for f in [RESTART_STATE_FILE, RESTART_STATE_LOCK_FILE]:
            if os.path.exists(f):
                os.remove(f)
    
    def tearDown(self):
        """Clean up after tests"""
        for f in [RESTART_STATE_FILE, RESTART_STATE_LOCK_FILE]:
            if os.path.exists(f):
                os.remove(f)
    
    def test_save_state_returns_tuple(self):
        """Test that save_restart_state returns a tuple"""
        result = save_restart_state_standalone()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], bool)
        self.assertIsInstance(result[1], str)
    
    def test_validate_returns_tuple(self):
        """Test that validate_restart_prerequisites returns a tuple"""
        result = validate_restart_prerequisites_standalone()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result[0], bool)
        self.assertIsInstance(result[1], str)
        self.assertIsInstance(result[2], int)
    
    def test_load_state_handles_permission_error(self):
        """Test that load_restart_state handles permission errors gracefully"""
        # Create a state file
        save_restart_state_standalone(updated_files=['test.py'])
        
        # Try to make it unreadable
        try:
            os.chmod(RESTART_STATE_FILE, 0o000)
            # This should not raise, but return None
            state = load_restart_state_standalone()
            # On some systems this might still work
        except PermissionError:
            pass
        finally:
            # Restore permissions
            try:
                os.chmod(RESTART_STATE_FILE, 0o644)
            except:
                pass


def run_tests():
    """Run all tests and return results"""
    # Create a test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestRestartPrerequisites))
    suite.addTests(loader.loadTestsFromTestCase(TestRestartState))
    suite.addTests(loader.loadTestsFromTestCase(TestRestartErrorCodes))
    suite.addTests(loader.loadTestsFromTestCase(TestEntryPointValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("RESTART FUNCTIONALITY TESTS (STANDALONE)")
    print("=" * 60)
    
    result = run_tests()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total - failures - errors
    
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failures: {failures}")
    print(f"Errors: {errors}")
    
    if failures == 0 and errors == 0:
        print("\n🎉 All restart functionality tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️ {failures + errors} test(s) failed. Please review the implementation.")
        sys.exit(1)
