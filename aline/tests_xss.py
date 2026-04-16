"""
tests_xss.py — Stored XSS Prevention Tests

Verifies that user-controlled profile content (bio field) is never executed
as HTML/JavaScript when rendered by the application.

Assignment: Fix Stored XSS in User-Controlled Profile Content
Branch:     assignment/fix-stored-xss-profile-content
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from .models import UserProfile


class StoredXSSProfileBioTests(TestCase):
    """
    Tests that XSS payloads stored in the bio field are properly escaped
    when the profile page renders them.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='xsstest',
            email='xss@test.com',
            password='TestPass123!'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            student_id='XSS001',
        )
        self.client.login(username='xsstest', password='TestPass123!')

    # -------------------------------------------------------------------------
    # Helper
    # -------------------------------------------------------------------------
    def _post_bio(self, payload):
        """Submit profile form with the given bio payload and return response."""
        return self.client.post(
            reverse('aline:profile'),
            data={
                'first_name': 'Test',
                'last_name': 'User',
                'email': 'xss@test.com',
                'student_id': 'XSS001',
                'phone_number': '',
                'bio': payload,
                'date_of_birth': '',
            },
            follow=True,
        )

    # -------------------------------------------------------------------------
    # Classic script tag
    # -------------------------------------------------------------------------
    def test_script_tag_escaped_on_profile_page(self):
        """
        A <script> tag in bio must be HTML-escaped, not executed.
        """
        payload = "<script>alert('xss')</script>"
        self._post_bio(payload)

        # Refresh profile page
        response = self.client.get(reverse('aline:profile'))
        content = response.content.decode()

        # Raw payload must NOT appear
        self.assertNotIn('<script>alert(', content,
                         "Raw <script> tag should not be present — escaping failed!")

        # Escaped form must be present
        self.assertIn('&lt;script&gt;', content,
                      "Escaped entity &lt;script&gt; should appear — escaping not applied!")

    # -------------------------------------------------------------------------
    # img onerror vector
    # -------------------------------------------------------------------------
    def test_img_onerror_escaped_on_profile_page(self):
        """
        An img onerror payload must be escaped, not interpreted as HTML.
        """
        payload = '"><img src=x onerror=alert(document.cookie)>'
        self._post_bio(payload)

        response = self.client.get(reverse('aline:profile'))
        content = response.content.decode()

        self.assertNotIn('<img src=x onerror=', content,
                         "img onerror tag must not appear unescaped")
        # The quote should be escaped to &quot; or &#x27;
        self.assertTrue(
            '&quot;' in content or '&#x27;' in content or '&lt;img' in content,
            "HTML entities for quotes/brackets must appear"
        )

    # -------------------------------------------------------------------------
    # SVG XSS
    # -------------------------------------------------------------------------
    def test_svg_xss_escaped_on_profile_page(self):
        """
        SVG-based XSS payload must be escaped.
        """
        payload = "<svg/onload=alert(1)>"
        self._post_bio(payload)

        response = self.client.get(reverse('aline:profile'))
        content = response.content.decode()

        self.assertNotIn('<svg/onload=', content,
                         "SVG onload payload must not appear unescaped")
        self.assertIn('&lt;svg', content,
                      "SVG tag should appear as escaped entity")

    # -------------------------------------------------------------------------
    # Legitimate content still works
    # -------------------------------------------------------------------------
    def test_legitimate_bio_renders_correctly(self):
        """
        Normal bio text must still render correctly after escaping.
        """
        payload = "I am a computer science student passionate about security."
        self._post_bio(payload)

        response = self.client.get(reverse('aline:profile'))
        content = response.content.decode()

        self.assertIn(payload, content,
                      "Legitimate bio text should appear unchanged on the profile page")

    # -------------------------------------------------------------------------
    # Max-length enforcement
    # -------------------------------------------------------------------------
    def test_bio_max_length_enforced(self):
        """
        Bio field must reject input longer than 500 characters.
        """
        long_payload = "A" * 501
        response = self._post_bio(long_payload)

        # Profile bio should not be updated
        self.profile.refresh_from_db()
        self.assertNotEqual(self.profile.bio, long_payload,
                            "Bio exceeding max_length should not be saved")

    # -------------------------------------------------------------------------
    # Ampersand and special character escaping
    # -------------------------------------------------------------------------
    def test_html_entities_escaped(self):
        """
        HTML special characters (&, <, >, \", ') must all be escaped.
        """
        payload = "AT&T <Rock> \"solid\" & 'safe'"
        self._post_bio(payload)

        response = self.client.get(reverse('aline:profile'))
        content = response.content.decode()

        # Raw entities must not appear as-is in HTML context
        # Django auto-escaping converts & → &amp;, < → &lt;, etc.
        self.assertIn('AT&amp;T', content,
                      "Ampersand should be escaped to &amp;")
        self.assertIn('&lt;Rock&gt;', content,
                      "Angle brackets should be escaped")


class StoredXSSAdminDetailTests(TestCase):
    """
    Verifies that XSS payloads stored in bio are escaped
    when a staff/admin views the user_detail page.
    """

    def setUp(self):
        self.client = Client()

        # Create regular user with malicious bio
        self.victim_user = User.objects.create_user(
            username='victim',
            email='victim@test.com',
            password='TestPass123!'
        )
        self.victim_profile = UserProfile.objects.create(
            user=self.victim_user,
            student_id='VIC001',
            bio="<script>alert('admin-xss')</script>",
        )

        # Create staff/admin user
        self.staff_user = User.objects.create_user(
            username='staffmember',
            email='staff@test.com',
            password='StaffPass123!',
            is_staff=True,
        )
        UserProfile.objects.create(
            user=self.staff_user,
            student_id='STF001',
        )
        staff_group, _ = Group.objects.get_or_create(name='Staff')
        self.staff_user.groups.add(staff_group)
        self.client.login(username='staffmember', password='StaffPass123!')

    def test_script_bio_escaped_on_admin_user_detail_page(self):
        """
        A malicious bio submitted by a student must be HTML-escaped when
        displayed on the admin user_detail page, not executed.
        """
        response = self.client.get(
            reverse('aline:user_detail', args=[self.victim_user.id])
        )
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)

        # Raw script tag must not appear
        self.assertNotIn("<script>alert('admin-xss')</script>", content,
                         "Raw <script> tag must not appear on admin user_detail page")

        # Escaped form must be present
        self.assertIn('&lt;script&gt;', content,
                      "Escaped entity should appear on admin page")
