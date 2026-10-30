"""Compatibility shim for tools that still call setup.py directly.

All package metadata lives in pyproject.toml.
"""

from setuptools import setup

setup()
