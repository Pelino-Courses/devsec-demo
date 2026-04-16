from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.password = "ComplexPass123!"
        self.user = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password=self.password,
        )

    def test_registration_creates_user_profile_and_logs_user_in(self):
        response = self.client.post(
            reverse("igihozo:register"),
            {
                "username": "newstudent",
                "first_name": "Igi",
                "last_name": "Hozo",
                "email": "newstudent@example.com",
                "display_name": "Igi Hozo",
                "bio": "Security-minded Django learner.",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("igihozo:account"))
        user = User.objects.get(username="newstudent")
        self.assertEqual(user.email, "newstudent@example.com")
        self.assertEqual(user.profile.display_name, "Igi Hozo")
        self.assertTrue(response.context["user"].is_authenticated)

    def test_registration_rejects_duplicate_email(self):
        response = self.client.post(
            reverse("igihozo:register"),
            {
                "username": "anotheruser",
                "email": "existing@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "An account with this email address already exists.")

    def test_login_and_logout_flow(self):
        login_response = self.client.post(
            reverse("igihozo:login"),
            {"username": "existinguser", "password": self.password},
            follow=True,
        )
        self.assertRedirects(login_response, reverse("igihozo:account"))
        self.assertTrue(login_response.context["user"].is_authenticated)

        logout_response = self.client.post(reverse("igihozo:logout"), follow=True)
        self.assertEqual(logout_response.status_code, 200)
        self.assertFalse(logout_response.context["user"].is_authenticated)
        self.assertContains(logout_response, "signed out")

    def test_account_page_requires_authentication(self):
        response = self.client.get(reverse("igihozo:account"))

        self.assertRedirects(
            response,
            f"{reverse('igihozo:login')}?next={reverse('igihozo:account')}",
        )

    def test_authenticated_user_can_update_profile(self):
        self.client.login(username="existinguser", password=self.password)

        response = self.client.post(
            reverse("igihozo:account"),
            {
                "email": "updated@example.com",
                "first_name": "Updated",
                "last_name": "Student",
                "display_name": "Updated Student",
                "bio": "Updated bio",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("igihozo:account"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertEqual(self.user.profile.display_name, "Updated Student")

    def test_password_change_updates_credentials(self):
        self.client.login(username="existinguser", password=self.password)

        response = self.client.post(
            reverse("igihozo:password_change"),
            {
                "old_password": self.password,
                "new_password1": "EvenStronger123!",
                "new_password2": "EvenStronger123!",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("igihozo:password_change_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("EvenStronger123!"))
