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


# ── IDOR (Insecure Direct Object Reference) Protection Tests ─────────────────

class IDORProtectionViewUserProfileTests(TestCase):
    """Test IDOR protection for the view_user_profile endpoint."""

    def setUp(self):
        self.client = Client()
        self.student1 = User.objects.create_user(
            username="student1", email="student1@test.com", password="test123"
        )
        self.student2 = User.objects.create_user(
            username="student2", email="student2@test.com", password="test123"
        )
        self.instructor_group = make_instructor_group()
        self.instructor = User.objects.create_user(
            username="instructor1", email="instructor1@test.com", password="test123"
        )
        self.instructor.groups.add(self.instructor_group)
        self.instructor = User.objects.get(pk=self.instructor.pk)
        Profile.objects.create(user=self.student1, bio="Student 1 bio")
        Profile.objects.create(user=self.student2, bio="Student 2 bio")
        Profile.objects.create(user=self.instructor, bio="Instructor bio")

    def test_student_can_view_own_profile(self):
        """Test that a student can view their own profile."""
        self.client.login(username="student1", password="test123")
        response = self.client.get(
            reverse("uwamahoro_joseline:view_user_profile", args=[self.student1.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "student1@test.com")

    def test_student_cannot_view_other_student_profile(self):
        """Test that a student CANNOT view another student's profile (IDOR prevention)."""
        self.client.login(username="student1", password="test123")
        response = self.client.get(
            reverse("uwamahoro_joseline:view_user_profile", args=[self.student2.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_instructor_can_view_any_profile(self):
        """Test that an instructor WITH can_view_all_profiles can view any profile."""
        self.client.login(username="instructor1", password="test123")
        response = self.client.get(
            reverse("uwamahoro_joseline:view_user_profile", args=[self.student1.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "student1@test.com")

    def test_unauthenticated_cannot_view_profile(self):
        """Test that unauthenticated users are redirected to login."""
        response = self.client.get(
            reverse("uwamahoro_joseline:view_user_profile", args=[self.student1.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_view_nonexistent_user_profile_returns_404(self):
        """Test that viewing a nonexistent user's profile returns 404."""
        self.client.login(username="student1", password="test123")
        response = self.client.get(
            reverse("uwamahoro_joseline:view_user_profile", args=[99999])
        )
        self.assertEqual(response.status_code, 404)

    def test_instructor_can_view_own_profile_via_specific_endpoint(self):
        """Test that instructors can view their own profile via the view_user_profile endpoint."""
        self.client.login(username="instructor1", password="test123")
        response = self.client.get(
            reverse("uwamahoro_joseline:view_user_profile", args=[self.instructor.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "instructor1@test.com")


class IDORProtectionEditUserAccountTests(TestCase):
    """Test IDOR protection for the edit_user_account endpoint."""

    def setUp(self):
        self.client = Client()
        self.student1 = User.objects.create_user(
            username="student1", email="student1@test.com", password="test123"
        )
        self.student2 = User.objects.create_user(
            username="student2", email="student2@test.com", password="test123"
        )
        self.instructor_group = make_instructor_group()
        self.instructor = User.objects.create_user(
            username="instructor1", email="instructor1@test.com", password="test123"
        )
        self.instructor.groups.add(self.instructor_group)
        self.instructor = User.objects.get(pk=self.instructor.pk)

    def test_student_can_edit_own_account(self):
        """Test that a student can edit their own account."""
        self.client.login(username="student1", password="test123")
        new_email = "newemail@test.com"
        response = self.client.post(
            reverse("uwamahoro_joseline:edit_user_account", args=[self.student1.pk]),
            {"email": new_email},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.student1.refresh_from_db()
        self.assertEqual(self.student1.email, new_email)

    def test_student_cannot_edit_other_student_account(self):
        """Test that a student CANNOT edit another student's account (IDOR prevention)."""
        self.client.login(username="student1", password="test123")
        original_email = self.student2.email
        response = self.client.post(
            reverse("uwamahoro_joseline:edit_user_account", args=[self.student2.pk]),
            {"email": "hacker@test.com"},
        )
        self.assertEqual(response.status_code, 403)
        self.student2.refresh_from_db()
        self.assertEqual(self.student2.email, original_email)

    def test_student_cannot_edit_instructor_account(self):
        """Test that a student CANNOT edit an instructor's account."""
        self.client.login(username="student1", password="test123")
        original_email = self.instructor.email
        response = self.client.post(
            reverse("uwamahoro_joseline:edit_user_account", args=[self.instructor.pk]),
            {"email": "hacker@test.com"},
        )
        self.assertEqual(response.status_code, 403)
        self.instructor.refresh_from_db()
        self.assertEqual(self.instructor.email, original_email)

    def test_unauthenticated_cannot_edit_account(self):
        """Test that unauthenticated users cannot edit accounts."""
        response = self.client.post(
            reverse("uwamahoro_joseline:edit_user_account", args=[self.student1.pk]),
            {"email": "hacker@test.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_edit_nonexistent_user_account_returns_404(self):
        """Test that editing a nonexistent user's account returns 404."""
        self.client.login(username="student1", password="test123")
        response = self.client.post(
            reverse("uwamahoro_joseline:edit_user_account", args=[99999]),
            {"email": "test@test.com"},
        )
        self.assertEqual(response.status_code, 404)

    def test_instructor_cannot_edit_other_instructor_account(self):
        """Test that instructors cannot edit other instructors' accounts (enforce object-level access)."""
        instructor2 = User.objects.create_user(
            username="instructor2", email="instructor2@test.com", password="test123"
        )
        instructor2.groups.add(self.instructor_group)
        self.client.login(username="instructor1", password="test123")
        original_email = instructor2.email
        response = self.client.post(
            reverse("uwamahoro_joseline:edit_user_account", args=[instructor2.pk]),
            {"email": "hacker@test.com"},
        )
        self.assertEqual(response.status_code, 403)
        instructor2.refresh_from_db()
        self.assertEqual(instructor2.email, original_email)


class IDORProtectionPromoteUserTests(TestCase):
    """Test IDOR protection for the promote_user endpoint."""

    def setUp(self):
        self.client = Client()
        self.student1 = User.objects.create_user(
            username="student1", password="test123"
        )
        self.student2 = User.objects.create_user(
            username="student2", password="test123"
        )
        self.instructor_group = make_instructor_group()
        self.instructor = User.objects.create_user(
            username="instructor1", password="test123"
        )
        self.instructor.groups.add(self.instructor_group)
        self.instructor = User.objects.get(pk=self.instructor.pk)

    def test_instructor_can_promote_student(self):
        """Test that an instructor WITH can_manage_users can promote a student."""
        self.client.login(username="instructor1", password="test123")
        response = self.client.post(
            reverse("uwamahoro_joseline:promote_user", args=[self.student1.pk]),
            {"action": "promote"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.student1.groups.filter(name="Instructor").exists())

    def test_student_cannot_promote_other_student(self):
        """Test that a student CANNOT promote another student."""
        self.client.login(username="student1", password="test123")
        response = self.client.post(
            reverse("uwamahoro_joseline:promote_user", args=[self.student2.pk]),
            {"action": "promote"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(self.student2.groups.filter(name="Instructor").exists())

    def test_instructor_cannot_promote_self(self):
        """Test that an instructor cannot promote/demote themselves (self-modification prevention)."""
        self.client.login(username="instructor1", password="test123")
        response = self.client.post(
            reverse("uwamahoro_joseline:promote_user", args=[self.instructor.pk]),
            {"action": "demote"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        messages_list = list(response.context["messages"])
        self.assertTrue(
            any("cannot modify your own role" in str(m).lower() for m in messages_list)
        )
        self.instructor.refresh_from_db()
        self.assertTrue(self.instructor.groups.filter(name="Instructor").exists())

    def test_promote_nonexistent_user_returns_404(self):
        """Test that promoting a nonexistent user returns 404."""
        self.client.login(username="instructor1", password="test123")
        response = self.client.post(
            reverse("uwamahoro_joseline:promote_user", args=[99999]),
            {"action": "promote"},
        )
        self.assertEqual(response.status_code, 404)


# ── Secure Password Reset Tests ──────────────────────────────────────────────

class PasswordResetRequestTests(TestCase):
    """Test secure password reset request flow."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("uwamahoro_joseline:password_reset")
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="OldPass123!"
        )

    def test_password_reset_page_loads_for_unauthenticated(self):
        """Test that unauthenticated users can access password reset page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset Your Password")

    def test_password_reset_with_valid_email(self):
        """Test password reset request with valid email in system."""
        response = self.client.post(
            self.url, {"email": "test@example.com"}, follow=True
        )
        # Should succeed and redirect to done page
        self.assertRedirects(
            response, reverse("uwamahoro_joseline:password_reset_done")
        )
        # Should display generic "check email" message (no user enumeration)
        self.assertContains(response, "Check Your Email")

    def test_password_reset_with_nonexistent_email(self):
        """Test password reset with non-existent email shows same message (prevents user enumeration)."""
        response = self.client.post(
            self.url, {"email": "nonexistent@example.com"}, follow=True
        )
        # Should succeed and redirect to done page (same as valid email)
        self.assertRedirects(
            response, reverse("uwamahoro_joseline:password_reset_done")
        )
        # Should display same message regardless of email existence
        self.assertContains(response, "Check Your Email")

    def test_password_reset_with_invalid_email_format(self):
        """Test password reset with invalid email format is rejected."""
        response = self.client.post(self.url, {"email": "not-an-email"})
        # Should fail and show error
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "email", "Enter a valid email address.")

    def test_password_reset_post_only(self):
        """Test that password reset uses POST method for security."""
        # GET to password reset form should work
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_can_request_reset(self):
        """Test that unauthenticated users can request password reset."""
        response = self.client.post(
            self.url, {"email": "test@example.com"}, follow=True
        )
        self.assertRedirects(
            response, reverse("uwamahoro_joseline:password_reset_done")
        )

    def test_authenticated_can_request_reset(self):
        """Test that authenticated users can also request password reset."""
        self.client.login(username="testuser", password="OldPass123!")
        response = self.client.post(
            self.url, {"email": "test@example.com"}, follow=True
        )
        self.assertRedirects(
            response, reverse("uwamahoro_joseline:password_reset_done")
        )


class PasswordResetConfirmTests(TestCase):
    """Test secure password reset confirmation flow."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="OldPass123!"
        )
        self.done_url = reverse("uwamahoro_joseline:password_reset_done")
        
        # Generate a valid password reset token
        from django.contrib.auth.tokens import default_token_generator
        self.token = default_token_generator.make_token(self.user)
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        self.uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.confirm_url = reverse(
            "uwamahoro_joseline:password_reset_confirm",
            args=[self.uidb64, self.token],
        )

    def test_password_reset_confirm_page_loads_with_valid_token(self):
        """Test that password reset confirm page loads with valid token."""
        response = self.client.get(self.confirm_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Set New Password")

    def test_password_reset_confirm_with_invalid_token(self):
        """Test that invalid token shows error message."""
        invalid_url = reverse(
            "uwamahoro_joseline:password_reset_confirm",
            args=[self.uidb64, "invalid-token"],
        )
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid or Expired Link")

    def test_password_reset_with_valid_password(self):
        """Test successful password reset with valid new password."""
        new_password = "NewSecurePass456!"
        response = self.client.post(
            self.confirm_url,
            {
                "new_password1": new_password,
                "new_password2": new_password,
            },
            follow=True,
        )
        # Should succeed and redirect to complete page
        self.assertRedirects(
            response, reverse("uwamahoro_joseline:password_reset_complete")
        )
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        # Old password should not work
        self.assertFalse(self.user.check_password("OldPass123!"))

    def test_password_reset_with_weak_password(self):
        """Test that weak password is rejected."""
        weak_password = "123"  # Too short
        response = self.client.post(
            self.confirm_url,
            {
                "new_password1": weak_password,
                "new_password2": weak_password,
            },
        )
        # Should fail validation
        self.assertEqual(response.status_code, 200)
        # Verify password was NOT changed
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password(weak_password))

    def test_password_reset_with_mismatched_passwords(self):
        """Test that mismatched passwords are rejected."""
        response = self.client.post(
            self.confirm_url,
            {
                "new_password1": "NewPass123!",
                "new_password2": "DifferentPass123!",
            },
        )
        # Should fail
        self.assertEqual(response.status_code, 200)
        # Verify password was NOT changed
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password("NewPass123!"))

    def test_password_reset_with_password_same_as_username(self):
        """Test that password matching username is rejected."""
        response = self.client.post(
            self.confirm_url,
            {
                "new_password1": "testuser",
                "new_password2": "testuser",
            },
        )
        # Should fail
        self.assertEqual(response.status_code, 200)

    def test_token_is_one_time_use(self):
        """Test that reset token can only be used once."""
        new_password = "NewPass123!"
        # First use: success
        self.client.post(
            self.confirm_url,
            {
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )
        
        # Second use: should fail (token invalidated after first use)
        response = self.client.post(
            self.confirm_url,
            {
                "new_password1": "AnotherNewPass456!",
                "new_password2": "AnotherNewPass456!",
            },
        )
        # Should get invalid token message
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid or Expired Link")

    def test_can_login_after_password_reset(self):
        """Test that user can log in with new password after reset."""
        new_password = "NewPassword123!"
        
        # Reset password
        self.client.post(
            self.confirm_url,
            {
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )
        
        # Try to log in with new password
        response = self.client.post(
            reverse("uwamahoro_joseline:login"),
            {
                "username": "testuser",
                "password": new_password,
            },
        )
        # Should succeed and redirect to dashboard
        self.assertRedirects(response, reverse("uwamahoro_joseline:dashboard"))

    def test_cannot_login_with_old_password_after_reset(self):
        """Test that old password no longer works after reset."""
        new_password = "NewPassword123!"
        
        # Reset password
        self.client.post(
            self.confirm_url,
            {
                "new_password1": new_password,
                "new_password2": new_password,
            },
        )
        
        # Try to log in with old password
        response = self.client.post(
            reverse("uwamahoro_joseline:login"),
            {
                "username": "testuser",
                "password": "OldPass123!",
            },
        )
        # Should fail
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
