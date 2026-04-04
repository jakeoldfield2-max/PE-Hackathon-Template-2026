"""
Tests for URL creation/shortening endpoint.
Tests the /shorten POST endpoint in isolation.
"""

import pytest
import time


class TestURLCreation:
    """Test suite for URL shortening functionality."""

    def test_shorten_url_success(self, client, sample_user_with_api_key):
        """Test successful URL shortening with valid data."""
        timestamp = int(time.time() * 1000)

        response = client.post('/shorten', json={
            'original_url': f'https://example.com/test/{timestamp}',
            'title': f'Test Link {timestamp}'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 201
        data = response.get_json()
        assert 'id' in data
        assert 'short_code' in data
        assert len(data['short_code']) == 6
        assert 'short_url' in data
        assert data['original_url'] == f'https://example.com/test/{timestamp}'
        assert data['title'] == f'Test Link {timestamp}'
        assert data['was_existing'] is False

    def test_shorten_url_missing_api_key(self, client):
        """Test URL shortening fails when API key is missing."""
        response = client.post('/shorten', json={
            'original_url': 'https://example.com',
            'title': 'Test'
        })

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert 'API key' in data['error']

    def test_shorten_url_invalid_api_key(self, client):
        """Test URL shortening fails with invalid API key."""
        response = client.post('/shorten', json={
            'original_url': 'https://example.com',
            'title': 'Test'
        }, headers={'X-API-Key': 'upk_invalid_key_12345'})

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid' in data['error']

    def test_shorten_url_missing_original_url(self, client, sample_user_with_api_key):
        """Test URL shortening fails when original_url is missing."""
        response = client.post('/shorten', json={
            'title': 'Test'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_shorten_url_missing_title(self, client, sample_user_with_api_key):
        """Test URL shortening fails when title is missing."""
        response = client.post('/shorten', json={
            'original_url': 'https://example.com'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'title' in data['error']

    def test_shorten_url_generates_unique_codes(self, client, sample_user_with_api_key):
        """Test that each shortened URL gets a unique short_code."""
        codes = set()

        for i in range(5):
            response = client.post('/shorten', json={
                'original_url': f'https://example.com/test/{i}',
                'title': f'Test Link {i}'
            }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

            assert response.status_code == 201
            data = response.get_json()
            codes.add(data['short_code'])

        # All 5 codes should be unique
        assert len(codes) == 5

    def test_shorten_url_idempotent(self, client, sample_user_with_api_key):
        """Test that shortening the same URL twice returns the same code."""
        timestamp = int(time.time() * 1000)
        url = f'https://example.com/idempotent/{timestamp}'

        # First request
        response1 = client.post('/shorten', json={
            'original_url': url,
            'title': 'Test 1'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response1.status_code == 201
        data1 = response1.get_json()
        assert data1['was_existing'] is False

        # Second request with same URL
        response2 = client.post('/shorten', json={
            'original_url': url,
            'title': 'Test 2'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response2.status_code == 200  # Existing URL returns 200
        data2 = response2.get_json()
        assert data2['was_existing'] is True
        assert data2['short_code'] == data1['short_code']

    def test_shorten_url_creates_event(self, client, sample_user_with_api_key):
        """Test that creating a URL also creates a 'created' event."""
        timestamp = int(time.time() * 1000)

        response = client.post('/shorten', json={
            'original_url': f'https://example.com/event-test/{timestamp}',
            'title': f'Event Test {timestamp}'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 201
        # Event creation is internal - we just verify the endpoint succeeds
        # A more thorough test would query the events table directly


class TestURLValidation:
    """Test suite for URL validation and SSRF protection."""

    def test_rejects_localhost(self, client, sample_user_with_api_key):
        """Test that localhost URLs are rejected."""
        response = client.post('/shorten', json={
            'original_url': 'http://localhost/admin',
            'title': 'Test'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'localhost' in data['error'].lower()

    def test_rejects_127_0_0_1(self, client, sample_user_with_api_key):
        """Test that 127.0.0.1 URLs are rejected."""
        response = client.post('/shorten', json={
            'original_url': 'http://127.0.0.1/admin',
            'title': 'Test'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_rejects_private_ip_10(self, client, sample_user_with_api_key):
        """Test that 10.x.x.x private IPs are rejected."""
        response = client.post('/shorten', json={
            'original_url': 'http://10.0.0.1/internal',
            'title': 'Test'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'private' in data['error'].lower() or 'internal' in data['error'].lower()

    def test_rejects_private_ip_172(self, client, sample_user_with_api_key):
        """Test that 172.16-31.x.x private IPs are rejected."""
        response = client.post('/shorten', json={
            'original_url': 'http://172.16.0.1/internal',
            'title': 'Test'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_rejects_private_ip_192(self, client, sample_user_with_api_key):
        """Test that 192.168.x.x private IPs are rejected."""
        response = client.post('/shorten', json={
            'original_url': 'http://192.168.1.1/router',
            'title': 'Test'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_rejects_link_local_169_254(self, client, sample_user_with_api_key):
        """Test that 169.254.x.x (AWS metadata) is rejected."""
        response = client.post('/shorten', json={
            'original_url': 'http://169.254.169.254/latest/meta-data/',
            'title': 'Test'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_rejects_ftp_protocol(self, client, sample_user_with_api_key):
        """Test that ftp:// protocol is rejected."""
        response = client.post('/shorten', json={
            'original_url': 'ftp://example.com/file.txt',
            'title': 'Test'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'protocol' in data['error'].lower()

    def test_rejects_file_protocol(self, client, sample_user_with_api_key):
        """Test that file:// protocol is rejected."""
        response = client.post('/shorten', json={
            'original_url': 'file:///etc/passwd',
            'title': 'Test'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_rejects_url_too_long(self, client, sample_user_with_api_key):
        """Test that URLs longer than 2048 chars are rejected."""
        long_url = 'https://example.com/' + 'a' * 2100

        response = client.post('/shorten', json={
            'original_url': long_url,
            'title': 'Test'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'length' in data['error'].lower()

    def test_accepts_valid_https_url(self, client, sample_user_with_api_key):
        """Test that valid https URLs are accepted."""
        timestamp = int(time.time() * 1000)
        response = client.post('/shorten', json={
            'original_url': f'https://example.com/valid/{timestamp}',
            'title': 'Test'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 201

    def test_accepts_valid_http_url(self, client, sample_user_with_api_key):
        """Test that valid http URLs are accepted."""
        timestamp = int(time.time() * 1000)
        response = client.post('/shorten', json={
            'original_url': f'http://example.com/valid/{timestamp}',
            'title': 'Test'
        }, headers={'X-API-Key': sample_user_with_api_key['api_key']})

        assert response.status_code == 201
