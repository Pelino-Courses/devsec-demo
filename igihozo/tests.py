from django.contrib.auth.models import Group, Permission, User
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

        self.assertRedirects(
            response,
            reverse("igihozo:profile_edit", kwargs={"username": "newstudent"}),
        )
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
        self.assertRedirects(
            login_response,
            reverse("igihozo:profile_edit", kwargs={"username": "existinguser"}),
        )
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
            reverse("igihozo:profile_edit", kwargs={"username": "existinguser"}),
            {
                "email": "updated@example.com",
                "first_name": "Updated",
                "last_name": "Student",
                "display_name": "Updated Student",
                "bio": "Updated bio",
            },
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("igihozo:profile_edit", kwargs={"username": "existinguser"}),
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertEqual(self.user.profile.display_name, "Updated Student")

    def test_account_route_redirects_to_owned_profile_edit_view(self):
        self.client.login(username="existinguser", password=self.password)

        response = self.client.get(reverse("igihozo:account"))

        self.assertRedirects(
            response,
            reverse("igihozo:profile_edit", kwargs={"username": "existinguser"}),
        )

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


class RoleBasedAccessControlTests(TestCase):
    def setUp(self):
        self.password = "ComplexPass123!"
        self.standard_user = User.objects.create_user(
            username="studentuser",
            email="student@example.com",
            password=self.password,
        )
        self.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password=self.password,
            is_staff=True,
        )
        self.instructor_user = User.objects.create_user(
            username="instructoruser",
            email="instructor@example.com",
            password=self.password,
        )
        self.instructors_group = Group.objects.get(name="instructors")
        self.students_group = Group.objects.get(name="students")
        self.instructor_user.groups.add(self.instructors_group)

    def test_new_users_are_assigned_to_student_group(self):
        self.assertTrue(self.standard_user.groups.filter(name="students").exists())

    def test_anonymous_user_cannot_access_privileged_dashboard(self):
        response = self.client.get(reverse("igihozo:privileged_dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('igihozo:login')}?next={reverse('igihozo:privileged_dashboard')}",
        )

    def test_authenticated_standard_user_gets_403_for_privileged_dashboard(self):
        self.client.login(username="studentuser", password=self.password)

        response = self.client.get(reverse("igihozo:privileged_dashboard"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "do not have permission", status_code=403)

    def test_instructor_group_user_can_access_privileged_dashboard(self):
        self.client.login(username="instructoruser", password=self.password)

        response = self.client.get(reverse("igihozo:privileged_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Privileged dashboard")
        self.assertContains(response, "studentuser")

    def test_staff_user_can_access_privileged_dashboard(self):
        self.client.login(username="staffuser", password=self.password)

        response = self.client.get(reverse("igihozo:privileged_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registered users")

    def test_instructor_group_receives_privileged_permission(self):
        permission = Permission.objects.get(codename="view_privileged_dashboard")

        self.assertTrue(self.instructors_group.permissions.filter(pk=permission.pk).exists())


class IdorProtectionTests(TestCase):
    def setUp(self):
        self.password = "ComplexPass123!"
        self.owner = User.objects.create_user(
            username="owneruser",
            email="owner@example.com",
            password=self.password,
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password=self.password,
        )
        self.instructor = User.objects.create_user(
            username="instructoridor",
            email="instructoridor@example.com",
            password=self.password,
        )
        Group.objects.get(name="instructors").user_set.add(self.instructor)

    def test_user_can_view_own_identifier_based_profile(self):
        self.client.login(username="owneruser", password=self.password)

        response = self.client.get(
            reverse("igihozo:profile_detail", kwargs={"username": "owneruser"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "owneruser")

    def test_user_cannot_view_another_users_profile_by_changing_url(self):
        self.client.login(username="owneruser", password=self.password)

        response = self.client.get(
            reverse("igihozo:profile_detail", kwargs={"username": "otheruser"})
        )

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_edit_another_users_profile_by_changing_url(self):
        self.client.login(username="owneruser", password=self.password)

        response = self.client.post(
            reverse("igihozo:profile_edit", kwargs={"username": "otheruser"}),
            {
                "email": "hijack@example.com",
                "first_name": "Hijack",
                "last_name": "Attempt",
                "display_name": "Hijack Attempt",
                "bio": "Trying to overwrite another profile.",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.other_user.refresh_from_db()
        self.assertEqual(self.other_user.email, "other@example.com")

    def test_privileged_user_can_view_another_users_profile_for_authorized_workflow(self):
        self.client.login(username="instructoridor", password=self.password)

        response = self.client.get(
            reverse("igihozo:profile_detail", kwargs={"username": "otheruser"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "otheruser")

    def test_privileged_user_can_edit_another_users_profile_for_authorized_workflow(self):
        self.client.login(username="instructoridor", password=self.password)

        response = self.client.post(
            reverse("igihozo:profile_edit", kwargs={"username": "otheruser"}),
            {
                "email": "reviewed@example.com",
                "first_name": "Reviewed",
                "last_name": "Student",
                "display_name": "Reviewed Student",
                "bio": "Updated by privileged workflow.",
            },
            follow=True,
        )

        self.assertRedirects(
            response,
            reverse("igihozo:profile_edit", kwargs={"username": "otheruser"}),
        )
        self.other_user.refresh_from_db()
        self.assertEqual(self.other_user.email, "reviewed@example.com")
