#!/usr/bin/env python3
"""
Real Test Coverage Analysis using pytest-cov
Runs actual tests and generates coverage reports.
"""

import subprocess
import json
import os
import sys
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed."""
    try:
        import coverage
        import pytest
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Install with: pip install pytest pytest-cov coverage")
        return False
    return True

def run_coverage_analysis(source_dir="src", test_dir="tests"):
    """Run pytest with coverage and generate reports."""
    
    print("🧪 Running tests with coverage analysis...")
    print("=" * 60)
    
    # Run pytest with coverage
    cmd = [
        "python", "-m", "pytest",
        test_dir,
        f"--cov={source_dir}",
        "--cov-report=term-missing",
        "--cov-report=json:coverage.json",
        "--cov-report=html:htmlcov",
        "-v"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def parse_coverage_json():
    """Parse the JSON coverage report."""
    coverage_file = "coverage.json"
    
    if not os.path.exists(coverage_file):
        print("❌ Coverage JSON file not found")
        return None
    
    try:
        with open(coverage_file, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"❌ Error reading coverage data: {e}")
        return None

def analyze_coverage_data(coverage_data):
    """Analyze and display coverage results."""
    
    if not coverage_data:
        return
    
    print("\n📊 DETAILED COVERAGE ANALYSIS")
    print("=" * 60)
    
    # Overall summary
    totals = coverage_data.get('totals', {})
    covered_lines = totals.get('covered_lines', 0)
    num_statements = totals.get('num_statements', 0)
    percent_covered = totals.get('percent_covered', 0)
    
    print(f"📈 OVERALL COVERAGE: {percent_covered:.1f}%")
    print(f"   Lines covered: {covered_lines}/{num_statements}")
    print(f"   Missing lines: {num_statements - covered_lines}")
    
    # File-by-file breakdown
    files = coverage_data.get('files', {})
    
    if files:
        print(f"\n📁 FILE BREAKDOWN ({len(files)} files)")
        print("-" * 60)
        
        # Sort files by coverage percentage (lowest first)
        sorted_files = sorted(
            files.items(), 
            key=lambda x: x[1].get('summary', {}).get('percent_covered', 0)
        )
        
        low_coverage = []
        no_coverage = []
        good_coverage = []
        
        for file_path, file_data in sorted_files:
            summary = file_data.get('summary', {})
            percent = summary.get('percent_covered', 0)
            covered = summary.get('covered_lines', 0)
            total = summary.get('num_statements', 0)
            missing = summary.get('missing_lines', 0)
            
            # Categorize by coverage level
            if percent == 0:
                no_coverage.append((file_path, percent, covered, total, missing))
            elif percent < 50:
                low_coverage.append((file_path, percent, covered, total, missing))
            else:
                good_coverage.append((file_path, percent, covered, total, missing))
            
            # Show missing lines for critical files
            missing_lines = file_data.get('missing_lines', [])
            if missing_lines and percent < 80:
                missing_str = ', '.join(map(str, missing_lines[:10]))
                if len(missing_lines) > 10:
                    missing_str += f" ... +{len(missing_lines) - 10} more"
        
        # Display results by category
        if no_coverage:
            print(f"\n🚨 NO COVERAGE ({len(no_coverage)} files):")
            for file_path, percent, covered, total, missing in no_coverage:
                rel_path = os.path.relpath(file_path)
                print(f"   {rel_path}: {percent:.1f}% ({covered}/{total} lines)")
        
        if low_coverage:
            print(f"\n⚠️  LOW COVERAGE ({len(low_coverage)} files):")
            for file_path, percent, covered, total, missing in low_coverage:
                rel_path = os.path.relpath(file_path)
                print(f"   {rel_path}: {percent:.1f}% ({covered}/{total} lines)")
        
        if good_coverage:
            print(f"\n✅ GOOD COVERAGE ({len(good_coverage)} files):")
            for file_path, percent, covered, total, missing in good_coverage[:10]:  # Show top 10
                rel_path = os.path.relpath(file_path)
                print(f"   {rel_path}: {percent:.1f}% ({covered}/{total} lines)")
            if len(good_coverage) > 10:
                print(f"   ... and {len(good_coverage) - 10} more files with good coverage")

def show_missing_lines_details(coverage_data):
    """Show specific missing lines for files with low coverage."""
    
    files = coverage_data.get('files', {})
    
    print(f"\n🎯 SPECIFIC LINES TO TEST")
    print("-" * 60)
    
    for file_path, file_data in files.items():
        summary = file_data.get('summary', {})
        percent = summary.get('percent_covered', 0)
        
        if percent < 80 and percent > 0:  # Show files with some but not good coverage
            missing_lines = file_data.get('missing_lines', [])
            if missing_lines:
                rel_path = os.path.relpath(file_path)
                print(f"\n📄 {rel_path} ({percent:.1f}% coverage):")
                
                # Group consecutive lines
                line_groups = []
                current_group = [missing_lines[0]] if missing_lines else []
                
                for line in missing_lines[1:]:
                    if line == current_group[-1] + 1:
                        current_group.append(line)
                    else:
                        line_groups.append(current_group)
                        current_group = [line]
                
                if current_group:
                    line_groups.append(current_group)
                
                # Display line groups
                for group in line_groups[:5]:  # Show first 5 groups
                    if len(group) == 1:
                        print(f"   Line {group[0]}")
                    else:
                        print(f"   Lines {group[0]}-{group[-1]} ({len(group)} lines)")
                
                if len(line_groups) > 5:
                    remaining_lines = sum(len(group) for group in line_groups[5:])
                    print(f"   ... and {remaining_lines} more untested lines")

def generate_recommendations(coverage_data):
    """Generate specific recommendations based on coverage data."""
    
    print(f"\n💡 RECOMMENDATIONS")
    print("-" * 60)
    
    files = coverage_data.get('files', {})
    totals = coverage_data.get('totals', {})
    overall_percent = totals.get('percent_covered', 0)
    
    if overall_percent < 50:
        print("🎯 IMMEDIATE PRIORITIES:")
        print("   1. Focus on API endpoints (user-facing functionality)")
        print("   2. Test critical business logic functions")
        print("   3. Add integration tests for complete workflows")
    elif overall_percent < 80:
        print("🎯 NEXT STEPS:")
        print("   1. Improve coverage for partially tested files")
        print("   2. Add edge case testing")
        print("   3. Test error handling paths")
    else:
        print("✅ GOOD COVERAGE! Consider:")
        print("   1. Add more integration tests")
        print("   2. Performance testing")
        print("   3. Security testing")
    
    # Specific file recommendations
    api_files_uncovered = [
        f for f in files.keys() 
        if '/apis/' in f and files[f].get('summary', {}).get('percent_covered', 0) < 50
    ]
    
    if api_files_uncovered:
        print(f"\n🚨 HIGH PRIORITY - Untested API Files:")
        for file_path in api_files_uncovered[:5]:
            rel_path = os.path.relpath(file_path)
            percent = files[file_path].get('summary', {}).get('percent_covered', 0)
            print(f"   - {rel_path} ({percent:.1f}% coverage)")

def main():
    """Main function."""
    
    print("🚀 Real Test Coverage Analysis")
    print("Project:", os.getcwd())
    print("-" * 60)
    
    if not check_dependencies():
        return
    
    # Run tests with coverage
    success = run_coverage_analysis()
    
    if not success:
        print("\n⚠️  Tests failed or had issues. Coverage data may be incomplete.")
    
    # Parse and analyze results
    coverage_data = parse_coverage_json()
    
    if coverage_data:
        analyze_coverage_data(coverage_data)
        show_missing_lines_details(coverage_data)
        generate_recommendations(coverage_data)
        
        print(f"\n📋 REPORTS GENERATED:")
        print(f"   - coverage.json (machine readable)")
        print(f"   - htmlcov/index.html (interactive HTML report)")
        print(f"   - Terminal output above")
        
    else:
        print("\n❌ Could not generate coverage analysis")
        print("Make sure tests are running successfully first")

if __name__ == "__main__":
    main()