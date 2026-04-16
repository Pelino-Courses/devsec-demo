#!/usr/bin/env python
"""Capture test output and print errors/failures cleanly."""
import subprocess, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
result = subprocess.run(
    [sys.executable, '../manage.py', 'test',
     'Munyabugingo.tests', 'Munyabugingo.tests_logging',
     '-v', '2', '--no-input'],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)
combined = result.stdout + result.stderr
# Print last 4000 chars to get error details
print(combined[-4000:])
print("\n--- EXIT CODE:", result.returncode)
