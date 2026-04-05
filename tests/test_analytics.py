"""
Tests for analytics and click tracking functionality.
Tests the stats endpoint and click counting.
"""

import pytest
import time

from app.models.event import Event


class TestClickAnalytics:
    """Test suite for click analytics functionality."""

    def test_stats_endpoint_returns_click_count(self, client, sample_url):
        """Test that stats endpoint returns click count."""
        response = client.get(f"/s/{sample_url['short_code']}/stats")

        assert response.status_code == 200
        data = response.get_json()
        assert 'short_code' in data
        assert data['short_code'] == sample_url['short_code']
        assert 'click_count' in data
        assert isinstance(data['click_count'], int)
        assert data['click_count'] >= 0

    def test_stats_endpoint_not_found(self, client):
        """Test stats endpoint returns 404 for non-existent URL."""
        response = client.get("/s/NOEXIST/stats")

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_redirect_increments_click_count(self, client, sample_url):
        """Test that visiting a short URL increments click count."""
        # Get initial count
        stats_before = client.get(f"/s/{sample_url['short_code']}/stats")
        count_before = stats_before.get_json()['click_count']

        # Visit the short URL (follow redirect)
        client.get(f"/s/{sample_url['short_code']}")

        # Get count after visit
        stats_after = client.get(f"/s/{sample_url['short_code']}/stats")
        count_after = stats_after.get_json()['click_count']

        assert count_after == count_before + 1

    def test_multiple_clicks_counted(self, client, sample_url):
        """Test that multiple visits are all counted."""
        # Get initial count
        stats_before = client.get(f"/s/{sample_url['short_code']}/stats")
        count_before = stats_before.get_json()['click_count']

        # Visit multiple times
        for _ in range(3):
            client.get(f"/s/{sample_url['short_code']}")

        # Get count after visits
        stats_after = client.get(f"/s/{sample_url['short_code']}/stats")
        count_after = stats_after.get_json()['click_count']

        assert count_after == count_before + 3

    def test_inactive_url_no_click_tracked(self, client, sample_url):
        """Test that clicks on inactive URLs return 410 but don't track."""
        # Deactivate the URL
        client.post('/update', json={
            'user_id': sample_url['user_id'],
            'url_id': sample_url['id'],
            'field': 'is_active',
            'new_value': False
        })

        # Try to visit (should get 410)
        response = client.get(f"/s/{sample_url['short_code']}")
        assert response.status_code == 410


class TestURLRedirect:
    """Test suite for URL redirect functionality."""

    def test_redirect_active_url(self, client, sample_url):
        """Test that active URLs redirect correctly."""
        response = client.get(f"/s/{sample_url['short_code']}")

        assert response.status_code == 302
        assert 'Location' in response.headers

    def test_redirect_inactive_url_returns_410(self, client, sample_url):
        """Test that inactive URLs return 410 Gone."""
        # Deactivate the URL
        client.post('/update', json={
            'user_id': sample_url['user_id'],
            'url_id': sample_url['id'],
            'field': 'is_active',
            'new_value': False
        })

        response = client.get(f"/s/{sample_url['short_code']}")

        assert response.status_code == 410
        data = response.get_json()
        assert 'deactivated' in data['error'].lower()

    def test_redirect_nonexistent_url_returns_404(self, client):
        """Test that non-existent URLs return 404."""
        response = client.get("/s/NOEXIST")

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data

    def test_url_info_endpoint(self, client, sample_url):
        """Test the URL info endpoint returns details."""
        response = client.get(f"/s/{sample_url['short_code']}/info")

        assert response.status_code == 200
        data = response.get_json()
        assert data['short_code'] == sample_url['short_code']
        assert 'original_url' in data
        assert 'title' in data
        assert 'is_active' in data


def test_redirect_persists_click_event_record(client, sample_url):
    before = Event.select().where(
        (Event.url_id == sample_url["id"]) & (Event.event_type == "click")
    ).count()

    response = client.get(f"/s/{sample_url['short_code']}", follow_redirects=False)
    assert response.status_code in (301, 302)

    after = Event.select().where(
        (Event.url_id == sample_url["id"]) & (Event.event_type == "click")
    ).count()
    assert after == before + 1
