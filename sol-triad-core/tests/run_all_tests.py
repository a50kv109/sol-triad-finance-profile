#!/usr/bin/env python3
"""
Единый автономный раннер тестов SOL-Triad Core.
Запускается стандартным интерпретатором Python 3 без внешних зависимостей:
    python3 tests/run_all_tests.py
"""

import sys
import os
import glob
import inspect
import importlib.util

# Добавляем пути в sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
sys.path.insert(0, BASE_DIR)


def run_all():
    print("=" * 80)
    print("   SOL-Triad Core — Master Verification Test Suite (v1.0.0-canonical)")
    print("=" * 80)

    test_pattern = os.path.join(BASE_DIR, "tests", "**", "test_*.py")
    test_files = sorted(glob.glob(test_pattern, recursive=True))

    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    failures = []

    for tf in test_files:
        rel_path = os.path.relpath(tf, BASE_DIR)
        mod_name = os.path.splitext(os.path.basename(tf))[0]

        spec = importlib.util.spec_from_file_location(mod_name, tf)
        if spec is None or spec.loader is None:
            print(f"[ERROR] Could not load spec for {rel_path}")
            continue

        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"[FAIL-LOAD] {rel_path}: {e}")
            failures.append((rel_path, "MODULE_LOAD", str(e)))
            continue

        # Поиск и вызов всех функций с префиксом test_
        test_funcs = [
            (name, obj) for name, obj in inspect.getmembers(mod)
            if name.startswith("test_") and inspect.isfunction(obj)
        ]

        print(f"\nSuite: {rel_path} ({len(test_funcs)} tests)")

        for name, func in test_funcs:
            sig = inspect.signature(func)
            if len(sig.parameters) != 0:
                continue

            total_tests += 1
            try:
                func()
                passed_tests += 1
                print(f"  [PASS] {name}")
            except Exception as e:
                failed_tests += 1
                failures.append((rel_path, name, str(e)))
                print(f"  [FAIL] {name}: {e}")

    print("\n" + "=" * 80)
    print(f"SUMMARY: Total Run: {total_tests} | Passed: {passed_tests} | Failed: {failed_tests}")
    print("=" * 80)

    if failures:
        print("\nFailures:")
        for suite, tname, err in failures:
            print(f"  - {suite} :: {tname} -> {err}")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED WITH 100% SUCCESS!")
        sys.exit(0)


if __name__ == "__main__":
    run_all()
