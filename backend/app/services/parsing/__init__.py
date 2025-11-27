"""Credit Engine 2.0 - Parsing Layer

This layer converts raw reports into NormalizedReport (SSOT #1).
All downstream modules MUST use NormalizedReport exclusively.
"""
from .html_parser import IdentityIQHTMLParser, parse_identityiq_html

__all__ = ["IdentityIQHTMLParser", "parse_identityiq_html"]
