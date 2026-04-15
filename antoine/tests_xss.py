"""
Tests for Stored XSS (Cross-Site Scripting) vulnerability prevention.

Verifies that user-controlled content is properly escaped and not executed
in the browser, while legitimate content renders correctly.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import UserProfile


class StoredXSSPreventionTests(TestCase):
    """Test that stored XSS vulnerabilities are prevented."""
    
    def setUp(self):
        self.client = Client()
        self.attacker = User.objects.create_user(
            username='attacker',
            email='attacker@example.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.attacker)
        
        self.victim = User.objects.create_user(
            username='victim',
            email='victim@example.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.victim)
    
    def test_xss_img_tag_in_bio_escaped(self):
        """Test that XSS img tag with onerror is escaped in bio."""
        profile = self.attacker.antoine_profile
        xss_payload = '<img src=x onerror="alert(\'XSS\')">'
        profile.bio = xss_payload
        profile.save()
        
        self.client.login(username='victim', password='testpass123')
        response = self.client.get(
            reverse('antoine:public_profile', kwargs={'user_id': self.attacker.id})
        )
        
        # Should contain escaped HTML
        self.assertContains(response, '&lt;img', status_code=200)
        # Should not execute the script
        self.assertNotIn('<img src=x onerror=', response.content.decode())
    
    def test_xss_script_tag_escaped(self):
        """Test that script tags are escaped."""
        profile = self.attacker.antoine_profile
        profile.bio = '<script>alert("XSS")</script>'
        profile.save()
        
        self.client.login(username='victim', password='testpass123')
        response = self.client.get(
            reverse('antoine:public_profile', kwargs={'user_id': self.attacker.id})
        )
        
        self.assertContains(response, '&lt;script&gt;', status_code=200)
        self.assertNotIn('<script>', response.content.decode())
    
    def test_xss_onclick_handler_escaped(self):
        """Test that onclick handlers are escaped."""
        profile = self.attacker.antoine_profile
        profile.bio = '<div onclick="alert(1)">Click</div>'
        profile.save()
        
        self.client.login(username='victim', password='testpass123')
        response = self.client.get(
            reverse('antoine:public_profile', kwargs={'user_id': self.attacker.id})
        )
        
        self.assertContains(response, '&lt;div', status_code=200)
        self.assertNotIn('<div onclick=', response.content.decode())
    
    def test_xss_svg_payload_escaped(self):
        """Test that SVG-based XSS is escaped."""
        profile = self.attacker.antoine_profile
        profile.bio = '<svg onload="alert(1)"></ svg>'
        profile.save()
        
        self.client.login(username='victim', password='testpass123')
        response = self.client.get(
            reverse('antoine:public_profile', kwargs={'user_id': self.attacker.id})
        )
        
        self.assertContains(response, '&lt;svg', status_code=200)
    
    def test_xss_multiple_events_escaped(self):
        """Test various event handlers are escaped."""
        profile = self.attacker.antoine_profile
        events = [
            '<body onload="alert(1)">',
            '<input onfocus="alert(1)">',
            '<textarea onchange="alert(1)">',
            '<div onmouseover="alert(1)">',
        ]
        
        for event_html in events:
            profile.bio = event_html
            profile.save()
            
            self.client.login(username='victim', password='testpass123')
            response = self.client.get(
                reverse('antoine:public_profile', kwargs={'user_id': self.attacker.id})
            )
            
            # All should be escaped
            self.assertContains(response, '&lt;', status_code=200)
            self.assertNotIn(event_html, response.content.decode())
            self.client.logout()
    
    def test_legitimate_bio_renders_correctly(self):
        """Test that legitimate text renders without being escaped."""
        profile = self.attacker.antoine_profile
        profile.bio = 'Software Engineer from California'
        profile.save()
        
        self.client.login(username='victim', password='testpass123')
        response = self.client.get(
            reverse('antoine:public_profile', kwargs={'user_id': self.attacker.id})
        )
        
        self.assertContains(response, 'Software Engineer from California', status_code=200)
    
    def test_bio_ampersand_escaped_once(self):
        """Test that ampersands are escaped exactly once."""
        profile = self.attacker.antoine_profile
        profile.bio = 'Tom & Jerry'
        profile.save()
        
        self.client.login(username='victim', password='testpass123')
        response = self.client.get(
            reverse('antoine:public_profile', kwargs={'user_id': self.attacker.id})
        )
        
        # Should have &amp; (escaped once), not &amp;amp; (double-escaped)
        self.assertContains(response, 'Tom &amp; Jerry', status_code=200)
        self.assertNotIn('Tom &amp;amp; Jerry', response.content.decode())
    
    def test_xss_in_first_name_escaped(self):
        """Test XSS in first name is escaped."""
        self.attacker.first_name = '<img src=x onerror="alert(1)">'
        self.attacker.save()
        
        self.client.login(username='victim', password='testpass123')
        response = self.client.get(
            reverse('antoine:public_profile', kwargs={'user_id': self.attacker.id})
        )
        
        self.assertContains(response, '&lt;img', status_code=200)
        self.assertNotIn('<img src=x', response.content.decode())
    
    def test_xss_in_last_name_escaped(self):
        """Test XSS in last name is escaped."""
        self.attacker.last_name = '<script>alert(1)</script>'
        self.attacker.save()
        
        self.client.login(username='victim', password='testpass123')
        response = self.client.get(
            reverse('antoine:public_profile', kwargs={'user_id': self.attacker.id})
        )
        
        self.assertContains(response, '&lt;script', status_code=200)
        self.assertNotIn('<script>', response.content.decode())


class XSSProductionBehaviorTests(TestCase):
    """Test XSS protection in live production scenarios."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user)
    
    def test_profile_update_with_xss_stored_safely(self):
        """Test that XSS payloads in form submissions are stored and displayed safely."""
        self.client.login(username='testuser', password='testpass123')
        
        # Submit form with XSS
        self.client.post(
            reverse('antoine:profile'),
            {
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'test@example.com',
                'phone_number': '123-456-7890',
                'bio': '<img src=x onerror="alert(\'XSS\')">'
            }
        )
        
        # Verify stored in database
        profile = self.user.antoine_profile
        profile.refresh_from_db()
        self.assertEqual(profile.bio, '<img src=x onerror="alert(\'XSS\')">')
        
        # But when displayed, should be escaped
        response = self.client.get(
            reverse('antoine:public_profile', kwargs={'user_id': self.user.id})
        )
        self.assertContains(response, '&lt;img', status_code=200)
        self.assertNotIn('<img src=x onerror=', response.content.decode())
    
    def test_dashboard_displays_safely(self):
        """Test that dashboard displays user content safely."""
        self.user.first_name = '<script>alert(1)</script>'
        self.user.save()
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('antoine:dashboard'))
        
        self.assertContains(response, '&lt;script', status_code=200)
        self.assertNotIn('<script>', response.content.decode())
    
    def test_login_history_user_agent_escaped(self):
        """Test that user agent in login history is escaped."""
        from .models import LoginHistory
        LoginHistory.objects.create(
            user=self.user,
            ip_address='127.0.0.1',
            user_agent='<script>alert(1)</script>',
            success=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('antoine:login_history'))
        
        self.assertContains(response, '&lt;script&gt;', status_code=200)
        self.assertNotIn('<script>alert(1)</script>', response.content.decode())
