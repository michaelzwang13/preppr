#!/usr/bin/env python3
"""
Comprehensive test runner for Preppr application.
Supports running different test categories, coverage reports, and CI/CD integration.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description or ' '.join(cmd)}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode != 0:
        print(f"\n❌ Command failed with exit code {result.returncode}")
        return False
    else:
        print(f"\n✅ Command completed successfully")
        return True


def get_test_categories():
    """Get available test categories from markers."""
    return {
        'unit': 'Fast unit tests (isolated, no external dependencies)',
        'integration': 'Integration tests (database, external services)',
        'api': 'API endpoint tests',
        'auth': 'Authentication and authorization tests',
        'nutrition': 'Nutrition tracking and goals tests',
        'subscription': 'Subscription and tier functionality tests',
        'tips': 'Tips system and rotation tests',
        'meal_planning': 'Meal planning and generation tests',
        'shopping': 'Shopping and cart functionality tests',
        'pantry': 'Pantry management tests',
        'recipes': 'Recipe and meal management tests',
        'admin': 'Admin and promotional code tests',
        'promo_codes': 'Promotional code validation and redemption tests',
        'premium': 'Premium tier specific functionality tests',
        'jwt': 'JWT authentication tests',
        'slow': 'Slow running tests (performance, large datasets)',
        'all': 'All tests'
    }


def main():
    parser = argparse.ArgumentParser(
        description='Run Preppr application tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python run_tests.py --category unit                 # Run only unit tests
  python run_tests.py --category api,nutrition        # Run API and nutrition tests
  python run_tests.py --coverage                      # Run all tests with coverage
  python run_tests.py --category integration --no-cov # Run integration tests without coverage
  python run_tests.py --fast                          # Run fast tests only (unit + api)
  python run_tests.py --ci                            # Run in CI mode (all tests, strict)
  python run_tests.py --file tests/test_nutrition.py  # Run specific test file
        '''
    )
    
    categories = get_test_categories()
    
    parser.add_argument(
        '--category', '-c',
        help=f'Test categories to run. Available: {", ".join(categories.keys())}',
        default='all'
    )
    
    parser.add_argument(
        '--file', '-f',
        help='Run specific test file(s)',
        nargs='*'
    )
    
    parser.add_argument(
        '--coverage', '--cov',
        action='store_true',
        help='Run with coverage report (default: true)'
    )
    
    parser.add_argument(
        '--no-coverage', '--no-cov',
        action='store_true',
        help='Run without coverage report'
    )
    
    parser.add_argument(
        '--html-cov',
        action='store_true',
        help='Generate HTML coverage report'
    )
    
    parser.add_argument(
        '--fast',
        action='store_true',
        help='Run fast tests only (unit + api, exclude slow tests)'
    )
    
    parser.add_argument(
        '--ci',
        action='store_true',
        help='Run in CI mode (strict, fail on warnings, full coverage)'
    )
    
    parser.add_argument(
        '--parallel', '-n',
        type=int,
        help='Run tests in parallel (number of workers)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='count',
        default=0,
        help='Increase verbosity (-v, -vv, -vvv)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Run in debug mode (no capture, pdb on failure)'
    )
    
    parser.add_argument(
        '--list-tests',
        action='store_true',
        help='List available tests without running them'
    )
    
    parser.add_argument(
        '--list-categories',
        action='store_true',
        help='List available test categories'
    )
    
    args = parser.parse_args()
    
    # List categories
    if args.list_categories:
        print("\nAvailable test categories:")
        print("=" * 50)
        for cat, desc in categories.items():
            print(f"{cat:15} - {desc}")
        return 0
    
    # Ensure we're in the project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Build pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Add test paths
    if args.file:
        cmd.extend(args.file)
    else:
        cmd.append('tests/')
    
    # Handle test categories
    if args.fast:
        cmd.extend(['-m', 'unit or api'])
        cmd.extend(['-m', 'not slow'])
    elif args.category and args.category != 'all':
        categories_list = [cat.strip() for cat in args.category.split(',')]
        marker_expr = ' or '.join(categories_list)
        cmd.extend(['-m', marker_expr])
    
    # Exclude slow tests unless explicitly requested
    if not args.ci and 'slow' not in args.category and not args.fast:
        if '-m' in cmd:
            # Find the marker expression and append to it
            marker_idx = cmd.index('-m') + 1
            cmd[marker_idx] = f"({cmd[marker_idx]}) and not slow"
        else:
            cmd.extend(['-m', 'not slow'])
    
    # Handle verbosity
    if args.verbose == 1:
        cmd.append('-v')
    elif args.verbose == 2:
        cmd.append('-vv')
    elif args.verbose >= 3:
        cmd.append('-vvv')
    
    # Handle coverage
    coverage_enabled = args.coverage or (not args.no_coverage and not args.debug)
    if coverage_enabled:
        cmd.extend(['--cov=src', '--cov-report=term-missing'])
        if args.html_cov or args.ci:
            cmd.append('--cov-report=html:htmlcov')
        if args.ci:
            cmd.extend(['--cov-fail-under=80', '--cov-branch'])
    
    # Handle parallel execution
    if args.parallel:
        cmd.extend(['-n', str(args.parallel)])
    
    # Handle debug mode
    if args.debug:
        cmd.extend(['--capture=no', '--pdb'])
    
    # Handle CI mode
    if args.ci:
        cmd.extend([
            '--strict-markers',
            '--strict-config',
            '--tb=short',
            '--maxfail=1',
            '--durations=20'
        ])
    
    # List tests
    if args.list_tests:
        cmd.append('--collect-only')
    
    # Set up environment for enhanced rollback system
    os.environ['TESTING'] = 'true'
    os.environ['FLASK_ENV'] = 'testing'
    
    # Run the tests
    print(f"\n🧪 Preppr Test Suite - Enhanced Database Rollback")
    print(f"{'='*60}")
    
    if args.list_tests:
        success = run_command(cmd, "Listing available tests")
    else:
        print(f"Category: {args.category}")
        print(f"Coverage: {'enabled' if coverage_enabled else 'disabled'}")
        print(f"Files: {args.file if args.file else 'all test files'}")
        print(f"Database: hacknyu25_test (automatic rollback enabled)")
        print(f"Environment: {os.environ.get('FLASK_ENV', 'not set')}")
        
        success = run_command(cmd, "Running tests with database rollback")
        
        if success:
            print(f"\n🎉 All tests passed!")
            print(f"✅ Database state automatically preserved")
            if coverage_enabled and args.html_cov:
                print(f"📊 HTML coverage report generated in htmlcov/index.html")
        else:
            print(f"\n💥 Some tests failed!")
            print(f"✅ Database state automatically rolled back")
            return 1
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())