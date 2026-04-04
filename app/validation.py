"""URL validation, SSRF protection, and API key authentication.

This module provides:
- URL validation (length, protocol, hostname)
- SSRF protection (blocks private IPs, localhost, link-local addresses)
- API key authentication decorator
- URL validation decorator for request handling
"""

import re
import ipaddress
import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import request, jsonify, g


# Maximum URL length (2048 is a common browser limit)
MAX_URL_LENGTH = 2048

# Allowed protocols for URLs
ALLOWED_PROTOCOLS = {'http', 'https'}

# Blocked hostnames (localhost variants)
BLOCKED_HOSTNAMES = {
    'localhost',
    'localhost.localdomain',
    '127.0.0.1',
    '::1',
    '0.0.0.0',
}


def _is_private_ip(ip_str):
    """Check if an IP address is private, loopback, or link-local.

    Blocks:
    - 127.x.x.x (loopback)
    - 10.x.x.x (private class A)
    - 172.16-31.x.x (private class B)
    - 192.168.x.x (private class C)
    - 169.254.x.x (link-local, AWS/cloud metadata)
    - IPv6 equivalents (::1, fe80::, fc00::, fd00::)
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private or
            ip.is_loopback or
            ip.is_link_local or
            ip.is_reserved or
            ip.is_multicast
        )
    except ValueError:
        # Not a valid IP address
        return False


def _extract_hostname_and_check_ip(hostname):
    """Extract hostname and check if it's a blocked IP address.

    Returns:
        (is_blocked, reason) tuple
    """
    # Remove port if present
    if ':' in hostname and not hostname.startswith('['):
        hostname = hostname.split(':')[0]

    # Handle IPv6 addresses in brackets
    if hostname.startswith('[') and hostname.endswith(']'):
        hostname = hostname[1:-1]

    # Check if it's a direct IP address
    if _is_private_ip(hostname):
        return True, f"Private/internal IP address not allowed: {hostname}"

    return False, None


def validate_url(url):
    """Validate a URL for basic requirements.

    Checks:
    - Length <= 2048 characters
    - Protocol is http or https only
    - Has valid hostname
    - Not localhost or direct localhost IP

    Args:
        url: The URL string to validate

    Returns:
        (is_valid, error_message) tuple
    """
    if not url:
        return False, "URL is required"

    if not isinstance(url, str):
        return False, "URL must be a string"

    # Check length
    if len(url) > MAX_URL_LENGTH:
        return False, f"URL exceeds maximum length of {MAX_URL_LENGTH} characters"

    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    # Check protocol
    if not parsed.scheme:
        return False, "URL must include a protocol (http or https)"

    if parsed.scheme.lower() not in ALLOWED_PROTOCOLS:
        return False, f"Invalid protocol '{parsed.scheme}'. Only http and https are allowed"

    # Check hostname exists
    if not parsed.netloc:
        return False, "URL must include a hostname"

    hostname = parsed.hostname
    if not hostname:
        return False, "Invalid hostname in URL"

    # Check for localhost
    if hostname.lower() in BLOCKED_HOSTNAMES:
        return False, f"Localhost URLs are not allowed"

    return True, None


def validate_url_ssrf(url):
    """Validate a URL with SSRF protection.

    Performs all checks from validate_url() plus:
    - Blocks private IP ranges (10.x.x.x, 172.16-31.x.x, 192.168.x.x)
    - Blocks link-local addresses (169.254.x.x - AWS/cloud metadata)
    - Blocks IPv6 private addresses (::1, fe80::, fc00::, fd00::)

    Args:
        url: The URL string to validate

    Returns:
        (is_valid, error_message) tuple
    """
    # First do basic validation
    is_valid, error = validate_url(url)
    if not is_valid:
        return False, error

    parsed = urlparse(url)
    hostname = parsed.hostname

    # Check if hostname is a blocked IP
    is_blocked, reason = _extract_hostname_and_check_ip(hostname)
    if is_blocked:
        return False, reason

    return True, None


def validate_url_decorator(f):
    """Decorator that validates original_url in request JSON.

    Expects request body to contain 'original_url' field.
    Returns 400 error if validation fails.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        data = request.get_json()
        if not data:
            return jsonify(error="Request body is required"), 400

        original_url = data.get("original_url")

        # Validate with SSRF protection
        is_valid, error = validate_url_ssrf(original_url)
        if not is_valid:
            return jsonify(error=error), 400

        return f(*args, **kwargs)
    return decorated_function


def require_api_key(f):
    """Decorator that requires valid API key in X-API-Key header.

    On success, sets g.authenticated_user to the User object.
    Returns 401 error if API key is missing or invalid.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Import here to avoid circular imports
        from app.models.user import User

        api_key = request.headers.get('X-API-Key')

        if not api_key:
            return jsonify(error="API key required. Include X-API-Key header"), 401

        # Validate API key format
        if not api_key.startswith('upk_'):
            return jsonify(error="Invalid API key format"), 401

        # Look up user by API key
        try:
            user = User.get(User.api_key == api_key)
            g.authenticated_user = user
        except User.DoesNotExist:
            return jsonify(error="Invalid API key"), 401

        return f(*args, **kwargs)
    return decorated_function
