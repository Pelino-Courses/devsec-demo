from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User, Group


class RegistrationTests(TestCase):
    def test_register_page_loads(self):
        response = self.client.get(reverse('tresor:register'))
        self.assertEqual(response.status_code, 200)

    def test_successful_registration(self):
        response = self.client.post(reverse('tresor:register'), {
            'username': 'tresortest',
            'first_name': 'Tresor',
            'last_name': 'Test',
            'email': 'tresor@test.com',
            'password1': 'Securepass123!',
            'password2': 'Securepass123!',
        })
        self.assertRedirects(response, reverse('tresor:dashboard'))
        self.assertTrue(User.objects.filter(username='tresortest').exists())

    def test_registration_password_mismatch(self):
        response = self.client.post(reverse('tresor:register'), {
            'username': 'tresortest',
            'first_name': 'Tresor',
            'last_name': 'Test',
            'email': 'tresor@test.com',
            'password1': 'Securepass123!',
            'password2': 'DifferentPass!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='tresortest').exists())

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username='tresortest', password='Pass123!')
        response = self.client.post(reverse('tresor:register'), {
            'username': 'tresortest',
            'first_name': 'Tresor',
            'last_name': 'Test',
            'email': 'other@test.com',
            'password1': 'Securepass123!',
            'password2': 'Securepass123!',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='tresortest').count(), 1)


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tresortest', password='Securepass123!'
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse('tresor:login'))
        self.assertEqual(response.status_code, 200)

    def test_successful_login(self):
        response = self.client.post(reverse('tresor:login'), {
            'username': 'tresortest',
            'password': 'Securepass123!',
        })
        self.assertRedirects(response, reverse('tresor:dashboard'))

    def test_wrong_password_rejected(self):
        response = self.client.post(reverse('tresor:login'), {
            'username': 'tresortest',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout(self):
        self.client.login(username='tresortest', password='Securepass123!')
        response = self.client.post(reverse('tresor:logout'))
        self.assertRedirects(response, reverse('tresor:login'))


class ProtectedPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tresortest', password='Securepass123!'
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('tresor:dashboard'))
        self.assertRedirects(response, f"/tresor/login/?next={reverse('tresor:dashboard')}")

    def test_profile_requires_login(self):
        response = self.client.get(reverse('tresor:profile'))
        self.assertRedirects(response, f"/tresor/login/?next={reverse('tresor:profile')}")

    def test_authenticated_user_accesses_dashboard(self):
        self.client.login(username='tresortest', password='Securepass123!')
        response = self.client.get(reverse('tresor:dashboard'))
        self.assertEqual(response.status_code, 200)


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tresortest', password='Securepass123!'
        )
        self.client.login(username='tresortest', password='Securepass123!')

    def test_password_change_page_loads(self):
        response = self.client.get(reverse('tresor:password_change'))
        self.assertEqual(response.status_code, 200)

    def test_successful_password_change(self):
        response = self.client.post(reverse('tresor:password_change'), {
            'old_password': 'Securepass123!',
            'new_password1': 'NewSecure456!',
            'new_password2': 'NewSecure456!',
        })
        self.assertRedirects(response, reverse('tresor:password_change_done'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecure456!'))

    def test_wrong_old_password_rejected(self):
        response = self.client.post(reverse('tresor:password_change'), {
            'old_password': 'wrongpassword',
            'new_password1': 'NewSecure456!',
            'new_password2': 'NewSecure456!',
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Securepass123!'))


class RBACTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username='student1', password='Securepass123!'
        )
        self.instructor = User.objects.create_user(
            username='instructor1', password='Securepass123!'
        )
        self.instructor_group, _ = Group.objects.get_or_create(name='instructor')
        self.instructor.groups.add(self.instructor_group)

    def test_anonymous_cannot_access_instructor_dashboard(self):
        response = self.client.get(reverse('tresor:instructor_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_student_cannot_access_instructor_dashboard(self):
        self.client.login(username='student1', password='Securepass123!')
        response = self.client.get(reverse('tresor:instructor_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_instructor_can_access_instructor_dashboard(self):
        self.client.login(username='instructor1', password='Securepass123!')
        response = self.client.get(reverse('tresor:instructor_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_staff_user_can_access_instructor_dashboard(self):
        staff = User.objects.create_user(
            username='staffuser', password='Securepass123!', is_staff=True
        )
        self.client.login(username='staffuser', password='Securepass123!')
        response = self.client.get(reverse('tresor:instructor_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_instructor_badge(self):
        self.client.login(username='instructor1', password='Securepass123!')
        response = self.client.get(reverse('tresor:dashboard'))
        self.assertContains(response, 'Instructor')

    def test_dashboard_shows_student_badge(self):
        self.client.login(username='student1', password='Securepass123!')
        response = self.client.get(reverse('tresor:dashboard'))
        self.assertContains(response, 'Student')

    def test_instructor_sees_all_users(self):
        self.client.login(username='instructor1', password='Securepass123!')
        response = self.client.get(reverse('tresor:instructor_dashboard'))
        self.assertContains(response, 'student1')


class IDORProfileViewTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='usera', password='Securepass123!'
        )
        self.user_b = User.objects.create_user(
            username='userb', password='Securepass123!'
        )
        self.instructor_group, _ = Group.objects.get_or_create(name='instructor')
        self.instructor = User.objects.create_user(
            username='instructor1', password='Securepass123!'
        )
        self.instructor.groups.add(self.instructor_group)

    def test_user_can_view_own_profile(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_view', kwargs={'username': 'usera'}))
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_view_other_users_profile(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_view', kwargs={'username': 'userb'}))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_view_profile(self):
        response = self.client.get(reverse('tresor:profile_view', kwargs={'username': 'usera'}))
        self.assertEqual(response.status_code, 302)

    def test_nonexistent_profile_returns_404(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_view', kwargs={'username': 'nobody'}))
        self.assertEqual(response.status_code, 404)

    def test_instructor_can_view_any_profile(self):
        self.client.login(username='instructor1', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_view', kwargs={'username': 'usera'}))
        self.assertEqual(response.status_code, 200)


class IDORProfileEditTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            username='usera', password='Securepass123!'
        )
        self.user_b = User.objects.create_user(
            username='userb', password='Securepass123!'
        )
        self.instructor_group, _ = Group.objects.get_or_create(name='instructor')
        self.instructor = User.objects.create_user(
            username='instructor1', password='Securepass123!'
        )
        self.instructor.groups.add(self.instructor_group)

    def test_user_can_edit_own_profile(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_edit', kwargs={'username': 'usera'}))
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_edit_other_users_profile(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_edit', kwargs={'username': 'userb'}))
        self.assertEqual(response.status_code, 403)

    def test_instructor_cannot_edit_other_users_profile(self):
        self.client.login(username='instructor1', password='Securepass123!')
        response = self.client.get(reverse('tresor:profile_edit', kwargs={'username': 'usera'}))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_edit_profile(self):
        response = self.client.get(reverse('tresor:profile_edit', kwargs={'username': 'usera'}))
        self.assertEqual(response.status_code, 302)

    def test_post_edit_saves_own_profile(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.post(
            reverse('tresor:profile_edit', kwargs={'username': 'usera'}),
            {'bio': 'My updated bio', 'first_name': 'User', 'last_name': 'A', 'email': 'usera@test.com'},
        )
        self.assertRedirects(response, reverse('tresor:profile_view', kwargs={'username': 'usera'}))
        self.user_a.profile.refresh_from_db()
        self.assertEqual(self.user_a.profile.bio, 'My updated bio')

    def test_post_cannot_edit_other_users_profile(self):
        self.client.login(username='usera', password='Securepass123!')
        response = self.client.post(
            reverse('tresor:profile_edit', kwargs={'username': 'userb'}),
            {'bio': 'Injected bio', 'first_name': 'Hacked', 'last_name': 'B', 'email': 'b@test.com'},
        )
        self.assertEqual(response.status_code, 403)
        self.user_b.profile.refresh_from_db()
        self.assertNotEqual(self.user_b.profile.bio, 'Injected bio')
