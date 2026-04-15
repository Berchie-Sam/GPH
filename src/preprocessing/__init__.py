"""
Preprocessing module for Ghana Parliamentary Hansard documents.

This module provides tools for parsing Hansard text, validating data quality,
enriching speaker information, and preparing data for LLM analysis.
"""

from .hansard_parser import HansardParser, Statement
from .validator import validate_hansard, TestResult
from .enrichment import enrich_hansard, build_reference_offline, build_reference_online
from .mp_reference import (
    scrape_parliament_gh,
    scrape_wikipedia,
    merge_sources,
    _normalise_name,
    _abbrev
)

__all__ = [
    'HansardParser',
    'Statement',
    'validate_hansard',
    'TestResult',
    'enrich_hansard',
    'build_reference_offline',
    'build_reference_online',
    'scrape_parliament_gh',
    'scrape_wikipedia',
    'merge_sources',
    '_normalise_name',
    '_abbrev',
]
