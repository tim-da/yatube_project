import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Profile

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class SignUpTest(TestCase):
    def test_signup_page_accessible(self):
        response = self.client.get(reverse('users:signup'))
        self.assertEqual(response.status_code, 200)

    def test_signup_uses_correct_template(self):
        response = self.client.get(reverse('users:signup'))
        self.assertTemplateUsed(response, 'users/signup.html')

    def test_signup_creates_user(self):
        user_count = User.objects.count()
        self.client.post(reverse('users:signup'), {
            'username': 'newuser',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
        })
        self.assertEqual(User.objects.count(), user_count + 1)

    def test_signup_creates_profile_automatically(self):
        self.client.post(reverse('users:signup'), {
            'username': 'profileauto',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
        })
        user = User.objects.get(username='profileauto')
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, Profile)


class LoginTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='loginuser', password='testpass123'
        )

    def test_login_page_accessible(self):
        response = self.client.get(reverse('users:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_uses_correct_template(self):
        response = self.client.get(reverse('users:login'))
        self.assertTemplateUsed(response, 'users/login.html')

    def test_logout_uses_correct_template(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('users:logout'))
        self.assertTemplateUsed(response, 'users/logged_out.html')

    def test_logout_get_not_allowed(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('users:logout'))
        self.assertEqual(response.status_code, 405)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ProfileTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='profuser', password='pass')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_edit_profile_accessible(self):
        response = self.client.get(reverse('users:edit_profile'))
        self.assertEqual(response.status_code, 200)

    def test_edit_profile_uses_correct_template(self):
        response = self.client.get(reverse('users:edit_profile'))
        self.assertTemplateUsed(response, 'users/edit_profile.html')

    def test_edit_profile_redirects_anonymous(self):
        self.client.logout()
        response = self.client.get(reverse('users:edit_profile'))
        self.assertEqual(response.status_code, 302)

    def test_edit_profile_saves_bio(self):
        self.client.post(reverse('users:edit_profile'), {'bio': 'Моя биография'})
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, 'Моя биография')

    def test_edit_profile_with_avatar(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile('avatar.gif', small_gif, 'image/gif')
        self.client.post(
            reverse('users:edit_profile'),
            {'bio': '', 'avatar': uploaded},
        )
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.avatar)

    def test_profile_page_shows_bio(self):
        self.user.profile.bio = 'Видимая биография'
        self.user.profile.save()
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        self.assertContains(response, 'Видимая биография')


class ErrorPageTest(TestCase):
    def test_404_page(self):
        response = self.client.get('/nonexistent-url-xyz/')
        self.assertEqual(response.status_code, 404)
