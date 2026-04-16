#!/usr/bin/env python
"""
Run RBAC tests for the aline application
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    os.environ['DJANGO_SETTINGS_MODULE'] = 'devsec_demo.settings'
    django.setup()
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2, interactive=False, keepdb=False)
    
    print("=" * 70)
    print("Running RBAC Test Suite")
    print("=" * 70)
    
    failures = test_runner.run_tests(['aline.tests_rbac'])
    
    print("=" * 70)
    if failures == 0:
        print("SUCCESS: All tests passed!")
    else:
        print("FAILURE: {} test(s) failed".format(failures))
    print("=" * 70)
    
    sys.exit(bool(failures))
