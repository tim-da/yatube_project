from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост длиннее пятнадцати символов',
        )

    def test_post_str(self):
        self.assertEqual(str(self.post), self.post.text[:15])

    def test_group_str(self):
        self.assertEqual(str(self.group), self.group.title)

    def test_post_verbose_name(self):
        self.assertEqual(Post._meta.get_field('text').verbose_name, 'text')

    def test_post_ordering(self):
        self.assertEqual(Post._meta.ordering, ['-pub_date'])


class PostURLTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.other_user = User.objects.create_user(username='other')
        cls.group = Group.objects.create(
            title='Группа',
            slug='test-group',
            description='Описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст поста',
            group=cls.group,
        )

    def setUp(self):
        self.guest = Client()
        self.author_client = Client()
        self.author_client.force_login(self.user)
        self.other_client = Client()
        self.other_client.force_login(self.other_user)

    def test_index_accessible(self):
        response = self.guest.get(reverse('posts:index'))
        self.assertEqual(response.status_code, 200)

    def test_group_page_accessible(self):
        response = self.guest.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.status_code, 200)

    def test_profile_accessible(self):
        response = self.guest.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        self.assertEqual(response.status_code, 200)

    def test_post_detail_accessible(self):
        response = self.guest.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_create_redirects_anonymous(self):
        response = self.guest.get(reverse('posts:post_create'))
        self.assertEqual(response.status_code, 302)

    def test_create_accessible_for_auth(self):
        response = self.author_client.get(reverse('posts:post_create'))
        self.assertEqual(response.status_code, 200)

    def test_edit_accessible_for_author(self):
        response = self.author_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_edit_redirects_non_author(self):
        response = self.other_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}),
        )


class PostViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='viewuser')
        cls.group = Group.objects.create(
            title='Группа',
            slug='view-group',
            description='Описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Текст поста для view-тестов',
            group=cls.group,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_index_uses_correct_template(self):
        response = self.client.get(reverse('posts:index'))
        self.assertTemplateUsed(response, 'posts/index.html')

    def test_group_uses_correct_template(self):
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertTemplateUsed(response, 'posts/group_list.html')

    def test_profile_uses_correct_template(self):
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.user.username})
        )
        self.assertTemplateUsed(response, 'posts/profile.html')

    def test_post_detail_uses_correct_template(self):
        response = self.client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertTemplateUsed(response, 'posts/post_detail.html')

    def test_create_post_uses_correct_template(self):
        response = self.client.get(reverse('posts:post_create'))
        self.assertTemplateUsed(response, 'posts/create_post.html')


class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='formuser')
        cls.group = Group.objects.create(
            title='Группа',
            slug='form-group',
            description='Описание',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_create_post(self):
        post_count = Post.objects.count()
        response = self.client.post(
            reverse('posts:post_create'),
            data={'text': 'Новый пост из теста'},
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user.username}),
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(Post.objects.filter(text='Новый пост из теста').exists())

    def test_edit_post(self):
        post = Post.objects.create(author=self.user, text='Исходный текст')
        response = self.client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.pk}),
            data={'text': 'Изменённый текст'},
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': post.pk}),
        )
        post.refresh_from_db()
        self.assertEqual(post.text, 'Изменённый текст')


class PaginatorTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='paguser')
        Post.objects.bulk_create([
            Post(author=cls.user, text=f'Пост {i}') for i in range(13)
        ])

    def test_first_page_has_10_posts(self):
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_has_3_posts(self):
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)
