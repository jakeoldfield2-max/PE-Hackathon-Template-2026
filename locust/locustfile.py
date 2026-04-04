"""
Run locust on web:
locust -f locust/locustfile.py --host=http://localhost:5000

Run locust on CLI: (u: number of users r: spawn rate, t: test duration)
locust -f locust/locustfile.py --host=http://localhost:5000 -u 50 -r 5 -t 5m
"""

from locust import HttpUser, task, between
import random
import string


class APILoadTest(HttpUser):
    """Load test user simulating real API usage patterns."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Create a user at the start of the test session."""
        self.user_id = None
        self.created_urls = []  # Track URLs for deletion/update tests
        self.create_new_user()
    
    def create_new_user(self):
        """Create a new user with a randomly generated username."""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        username = f"loadtest_user_{random_suffix}"
        email = f"{username}@loadtest.com"
        
        response = self.client.post('/users', json={
            'username': username,
            'email': email
        })
        
        if response.status_code == 201:
            data = response.json()
            self.user_id = data.get('id')
    
    @task(5)
    def create_user(self):
        """Create a new user (5x weight - frequently run)."""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        username = f"user_{random_suffix}"
        email = f"{username}@example.com"
        
        self.client.post('/users', json={
            'username': username,
            'email': email
        })
    
    @task(8)
    def shorten_url(self):
        """Create a shortened URL (8x weight - most common operation)."""
        if not self.user_id:
            self.create_new_user()
            if not self.user_id:
                return
        
        random_num = random.randint(1, 100000)
        title_suffix = ''.join(random.choices(string.ascii_lowercase, k=5))
        
        response = self.client.post('/shorten', json={
            'user_id': self.user_id,
            'original_url': f'https://example.com/page/{random_num}',
            'title': f'Link_{title_suffix}_{random_num}'
        })
        
        # Store created URL for later deletion/update tests
        if response.status_code == 201:
            data = response.json()
            self.created_urls.append({
                'id': data.get('id'),
                'title': data.get('title')
            })
            # Keep list from getting too large
            if len(self.created_urls) > 50:
                self.created_urls.pop(0)
    
    @task(3)
    def update_url(self):
        """Update a URL's title or is_active field (3x weight)."""
        if not self.created_urls or not self.user_id:
            return
        
        url = random.choice(self.created_urls)
        new_title = f"Updated_{random.randint(1, 1000)}"
        
        self.client.post('/update', json={
            'user_id': self.user_id,
            'url_id': url['id'],
            'field': 'title',
            'new_value': new_title
        })
    
    @task(2)
    def toggle_url_active(self):
        """Toggle URL active status (2x weight)."""
        if not self.created_urls or not self.user_id:
            return
        
        url = random.choice(self.created_urls)
        
        self.client.post('/update', json={
            'user_id': self.user_id,
            'url_id': url['id'],
            'field': 'is_active',
            'new_value': random.choice([True, False])
        })
    
    @task(4)
    def delete_url(self):
        """Delete a URL (4x weight)."""
        if not self.created_urls or not self.user_id:
            return
        
        url = self.created_urls.pop(0)  # Remove from tracking and delete
        
        self.client.post('/delete', json={
            'user_id': self.user_id,
            'title': url['title']
        })
    
    @task(2)
    def get_stats(self):
        """Get overall statistics (2x weight)."""
        self.client.get('/stats/total')
    
    @task(1)
    def health_check(self):
        """Health check endpoint (1x weight)."""
        self.client.get('/health')


class HighVolumeUser(HttpUser):
    """High-volume user focusing on URL shortening operations."""
    
    wait_time = between(0.5, 1.5)  # Faster requests
    
    def on_start(self):
        """Create a user at the start."""
        self.user_id = None
        self.create_new_user()
    
    def create_new_user(self):
        """Create a new user."""
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        username = f"highvolume_{random_suffix}"
        email = f"{username}@loadtest.com"
        
        response = self.client.post('/users', json={
            'username': username,
            'email': email
        })
        
        if response.status_code == 201:
            data = response.json()
            self.user_id = data.get('id')
    
    @task(95)
    def shorten_url(self):
        """Heavily favor URL shortening (95% of traffic)."""
        if not self.user_id:
            self.create_new_user()
            if not self.user_id:
                return
        
        random_num = random.randint(1, 1000000)
        
        self.client.post('/shorten', json={
            'user_id': self.user_id,
            'original_url': f'https://example.com/content/{random_num}',
            'title': f'Content_{random_num}'
        })
    
    @task(5)
    def health_check(self):
        """Health checks (5% of traffic)."""
        self.client.get('/health')
