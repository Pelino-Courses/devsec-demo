from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from .models import Profile


def make_instructor_group():
    """Helper: create the Instructor group with both RBAC permissions."""
    content_type = ContentType.objects.get_for_model(Profile)
    view_perm = Permission.objects.get(
        codename="can_view_all_profiles", content_type=content_type
    )
    manage_perm = Permission.objects.get(
        codename="can_manage_users", content_type=content_type
    )
    group, _ = Group.objects.get_or_create(name="Instructor")
    group.permissions.set([view_perm, manage_perm])
    return group


class RegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("uwamahoro_joseline:register")

    def test_registration_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create an account")

    def test_successful_registration(self):
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"))
        self.assertTrue(User.objects.filter(username="testuser").exists())
        self.assertTrue(Profile.objects.filter(user__username="testuser").exists())

    def test_registration_creates_profile(self):
        data = {
            "username": "profileuser",
            "email": "profile@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        self.client.post(self.url, data)
        user = User.objects.get(username="profileuser")
        self.assertTrue(hasattr(user, "profile"))

    def test_registration_with_mismatched_passwords(self):
        data = {
            "username": "baduser",
            "email": "bad@example.com",
            "password1": "SecurePass123!",
            "password2": "DifferentPass123!",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="baduser").exists())

    def test_registration_with_duplicate_username(self):
        User.objects.create_user(username="taken", password="SomePass123!")
        data = {
            "username": "taken",
            "email": "taken@example.com",
            "password1": "SecurePass123!",
            "password2": "SecurePass123!",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="taken").count(), 1)

    def test_authenticated_user_redirected_from_register(self):
        User.objects.create_user(username="existing", password="Pass123!")
        self.client.login(username="existing", password="Pass123!")
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"))


class LoginTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("uwamahoro_joseline:login")
        self.user = User.objects.create_user(username="loginuser", password="TestPass123!")

    def test_login_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_successful_login(self):
        data = {"username": "loginuser", "password": "TestPass123!"}
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"))

    def test_failed_login_wrong_password(self):
        data = {"username": "loginuser", "password": "WrongPassword!"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)

    def test_failed_login_unknown_user(self):
        data = {"username": "nobody", "password": "TestPass123!"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)

    def test_authenticated_user_redirected_from_login(self):
        self.client.login(username="loginuser", password="TestPass123!")
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"))

    def test_login_next_parameter_safe_redirect(self):
        data = {"username": "loginuser", "password": "TestPass123!"}
        safe_next = reverse("uwamahoro_joseline:profile")
        response = self.client.post(f"{self.url}?next={safe_next}", data)
        self.assertRedirects(response, safe_next)

    def test_login_next_parameter_rejects_external_url(self):
        data = {"username": "loginuser", "password": "TestPass123!"}
        response = self.client.post(
            self.url, {**data, "next": "http://evil.example.com/"}
        )
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"))


class LogoutTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("uwamahoro_joseline:logout")
        self.user = User.objects.create_user(username="logoutuser", password="TestPass123!")

    def test_logout_page_loads_for_authenticated_user(self):
        self.client.login(username="logoutuser", password="TestPass123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_successful_logout(self):
        self.client.login(username="logoutuser", password="TestPass123!")
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("uwamahoro_joseline:login"))
        response = self.client.get(reverse("uwamahoro_joseline:dashboard"))
        self.assertNotEqual(response.status_code, 200)


class AccessControlTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="authuser", password="TestPass123!")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("uwamahoro_joseline:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_profile_requires_login(self):
        response = self.client.get(reverse("uwamahoro_joseline:profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_password_change_requires_login(self):
        response = self.client.get(reverse("uwamahoro_joseline:password_change"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_dashboard_accessible_when_authenticated(self):
        self.client.login(username="authuser", password="TestPass123!")
        response = self.client.get(reverse("uwamahoro_joseline:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_profile_accessible_when_authenticated(self):
        self.client.login(username="authuser", password="TestPass123!")
        response = self.client.get(reverse("uwamahoro_joseline:profile"))
        self.assertEqual(response.status_code, 200)


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("uwamahoro_joseline:password_change")
        self.user = User.objects.create_user(username="pwuser", password="OldPass123!")
        self.client.login(username="pwuser", password="OldPass123!")

    def test_password_change_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Change password")

    def test_successful_password_change(self):
        data = {
            "old_password": "OldPass123!",
            "new_password1": "NewSecurePass456!",
            "new_password2": "NewSecurePass456!",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse("uwamahoro_joseline:password_change_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecurePass456!"))

    def test_password_change_wrong_old_password(self):
        data = {
            "old_password": "WrongOld!",
            "new_password1": "NewSecurePass456!",
            "new_password2": "NewSecurePass456!",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password("NewSecurePass456!"))

    def test_session_preserved_after_password_change(self):
        data = {
            "old_password": "OldPass123!",
            "new_password1": "NewSecurePass456!",
            "new_password2": "NewSecurePass456!",
        }
        self.client.post(self.url, data)
        response = self.client.get(reverse("uwamahoro_joseline:dashboard"))
        self.assertEqual(response.status_code, 200)


class ProfileTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="profileuser", email="pf@example.com", password="TestPass123!"
        )
        self.client.login(username="profileuser", password="TestPass123!")

    def test_profile_page_shows_username(self):
        response = self.client.get(reverse("uwamahoro_joseline:profile"))
        self.assertContains(response, "profileuser")

    def test_profile_page_shows_email(self):
        response = self.client.get(reverse("uwamahoro_joseline:profile"))
        self.assertContains(response, "pf@example.com")

    def test_profile_auto_creates_if_missing(self):
        response = self.client.get(reverse("uwamahoro_joseline:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())


# ── RBAC: Anonymous ───────────────────────────────────────────────────────────

class RBACAnonymousTests(TestCase):
    """Anonymous users are redirected to login for all protected routes."""

    def setUp(self):
        self.client = Client()
        self.target = User.objects.create_user(username="target", password="Pass123!")

    def test_instructor_panel_redirects_anonymous(self):
        response = self.client.get(reverse("uwamahoro_joseline:instructor_panel"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_promote_view_redirects_anonymous(self):
        response = self.client.post(
            reverse("uwamahoro_joseline:promote_user", args=[self.target.pk]),
            {"action": "promote"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_dashboard_redirects_anonymous(self):
        response = self.client.get(reverse("uwamahoro_joseline:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])


# ── RBAC: Student ─────────────────────────────────────────────────────────────

class RBACStudentTests(TestCase):
    """Authenticated students are blocked from instructor-only routes."""

    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(username="student", password="TestPass123!")
        self.target = User.objects.create_user(username="target", password="Pass123!")
        self.client.login(username="student", password="TestPass123!")

    def test_instructor_panel_forbidden_for_student(self):
        response = self.client.get(reverse("uwamahoro_joseline:instructor_panel"))
        self.assertEqual(response.status_code, 403)

    def test_promote_view_forbidden_for_student(self):
        response = self.client.post(
            reverse("uwamahoro_joseline:promote_user", args=[self.target.pk]),
            {"action": "promote"},
        )
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_gain_instructor_role_via_post(self):
        """Blocked student POST must not change the target's group membership."""
        group = make_instructor_group()
        self.client.post(
            reverse("uwamahoro_joseline:promote_user", args=[self.target.pk]),
            {"action": "promote"},
        )
        self.assertFalse(self.target.groups.filter(pk=group.pk).exists())

    def test_student_can_access_own_dashboard(self):
        response = self.client.get(reverse("uwamahoro_joseline:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_student_can_access_own_profile(self):
        response = self.client.get(reverse("uwamahoro_joseline:profile"))
        self.assertEqual(response.status_code, 200)


# ── RBAC: Instructor ──────────────────────────────────────────────────────────

class RBACInstructorTests(TestCase):
    """Instructors can access the panel and perform user management."""

    def setUp(self):
        self.client = Client()
        self.group = make_instructor_group()
        self.instructor = User.objects.create_user(
            username="instructor", password="TestPass123!"
        )
        self.student = User.objects.create_user(
            username="student", password="TestPass123!"
        )
        self.instructor.groups.add(self.group)
        # Reload to clear Django's per-request permission cache
        self.instructor = User.objects.get(pk=self.instructor.pk)
        self.client.login(username="instructor", password="TestPass123!")

    def test_instructor_can_access_panel(self):
        response = self.client.get(reverse("uwamahoro_joseline:instructor_panel"))
        self.assertEqual(response.status_code, 200)

    def test_instructor_panel_lists_all_users(self):
        response = self.client.get(reverse("uwamahoro_joseline:instructor_panel"))
        self.assertContains(response, "student")
        self.assertContains(response, "instructor")

    def test_instructor_can_promote_student(self):
        response = self.client.post(
            reverse("uwamahoro_joseline:promote_user", args=[self.student.pk]),
            {"action": "promote"},
        )
        self.assertRedirects(response, reverse("uwamahoro_joseline:instructor_panel"))
        self.assertTrue(self.student.groups.filter(pk=self.group.pk).exists())

    def test_instructor_can_demote_user(self):
        self.student.groups.add(self.group)
        response = self.client.post(
            reverse("uwamahoro_joseline:promote_user", args=[self.student.pk]),
            {"action": "demote"},
        )
        self.assertRedirects(response, reverse("uwamahoro_joseline:instructor_panel"))
        self.assertFalse(self.student.groups.filter(pk=self.group.pk).exists())

    def test_invalid_action_does_not_change_role(self):
        response = self.client.post(
            reverse("uwamahoro_joseline:promote_user", args=[self.student.pk]),
            {"action": "hack"},
        )
        self.assertRedirects(response, reverse("uwamahoro_joseline:instructor_panel"))
        self.assertFalse(self.student.groups.filter(pk=self.group.pk).exists())

    def test_promote_get_request_is_ignored(self):
        """GET to the promote URL should redirect without changing anything."""
        response = self.client.get(
            reverse("uwamahoro_joseline:promote_user", args=[self.student.pk])
        )
        self.assertRedirects(response, reverse("uwamahoro_joseline:instructor_panel"))
        self.assertFalse(self.student.groups.filter(pk=self.group.pk).exists())

    def test_instructor_can_still_access_student_pages(self):
        response = self.client.get(reverse("uwamahoro_joseline:dashboard"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("uwamahoro_joseline:profile"))
        self.assertEqual(response.status_code, 200)
