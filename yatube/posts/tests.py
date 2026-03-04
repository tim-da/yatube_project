import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Comment, Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


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

    def test_post_ordering(self):
        self.assertEqual(Post._meta.ordering, ['-pub_date'])

    def test_comment_str(self):
        comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            text='Тестовый комментарий',
        )
        self.assertEqual(str(comment), comment.text[:15])


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

    def test_follow_index_redirects_anonymous(self):
        response = self.guest.get(reverse('posts:follow_index'))
        self.assertEqual(response.status_code, 302)

    def test_follow_index_accessible_for_auth(self):
        response = self.author_client.get(reverse('posts:follow_index'))
        self.assertEqual(response.status_code, 200)


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

    def test_follow_index_uses_correct_template(self):
        response = self.client.get(reverse('posts:follow_index'))
        self.assertTemplateUsed(response, 'posts/follow.html')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
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

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

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

    def test_create_post_with_image(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='test.gif',
            content=small_gif,
            content_type='image/gif',
        )
        post_count = Post.objects.count()
        self.client.post(
            reverse('posts:post_create'),
            data={'text': 'Пост с картинкой', 'image': uploaded},
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(
            Post.objects.filter(text='Пост с картинкой').exists()
        )

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


class CommentTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='commentuser')
        cls.post = Post.objects.create(author=cls.user, text='Пост для комментов')

    def setUp(self):
        self.auth_client = Client()
        self.auth_client.force_login(self.user)
        self.guest = Client()

    def test_auth_user_can_comment(self):
        comment_count = Comment.objects.count()
        self.auth_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data={'text': 'Тестовый комментарий'},
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)

    def test_guest_cannot_comment(self):
        comment_count = Comment.objects.count()
        self.guest.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data={'text': 'Гостевой комментарий'},
        )
        self.assertEqual(Comment.objects.count(), comment_count)

    def test_comment_appears_on_post_detail(self):
        Comment.objects.create(
            post=self.post,
            author=self.user,
            text='Видимый комментарий',
        )
        response = self.auth_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertContains(response, 'Видимый комментарий')


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='follower')
        cls.author = User.objects.create_user(username='followed_author')
        cls.post = Post.objects.create(
            author=cls.author,
            text='Пост от автора',
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_user_can_follow(self):
        self.client.get(
            reverse('posts:profile_follow', kwargs={'username': self.author.username})
        )
        self.assertTrue(
            Follow.objects.filter(user=self.user, author=self.author).exists()
        )

    def test_user_can_unfollow(self):
        Follow.objects.create(user=self.user, author=self.author)
        self.client.get(
            reverse('posts:profile_unfollow', kwargs={'username': self.author.username})
        )
        self.assertFalse(
            Follow.objects.filter(user=self.user, author=self.author).exists()
        )

    def test_post_appears_in_follower_feed(self):
        Follow.objects.create(user=self.user, author=self.author)
        response = self.client.get(reverse('posts:follow_index'))
        self.assertIn(self.post, response.context['page_obj'])

    def test_post_not_in_non_follower_feed(self):
        other = User.objects.create_user(username='non_follower')
        self.client.force_login(other)
        response = self.client.get(reverse('posts:follow_index'))
        self.assertNotIn(self.post, response.context['page_obj'])


class PostDeleteTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='delete_author')
        cls.other = User.objects.create_user(username='delete_other')

    def setUp(self):
        self.post = Post.objects.create(
            author=self.author,
            text='Пост для удаления',
        )

    def test_author_can_delete_post(self):
        self.client.force_login(self.author)
        post_id = self.post.pk
        self.client.post(
            reverse('posts:post_delete', kwargs={'post_id': post_id})
        )
        self.assertFalse(Post.objects.filter(pk=post_id).exists())

    def test_delete_redirects_to_profile(self):
        self.client.force_login(self.author)
        response = self.client.post(
            reverse('posts:post_delete', kwargs={'post_id': self.post.pk})
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.author.username}),
        )

    def test_non_author_cannot_delete_post(self):
        self.client.force_login(self.other)
        post_id = self.post.pk
        self.client.post(
            reverse('posts:post_delete', kwargs={'post_id': post_id})
        )
        self.assertTrue(Post.objects.filter(pk=post_id).exists())

    def test_anonymous_cannot_delete_post(self):
        post_id = self.post.pk
        self.client.post(
            reverse('posts:post_delete', kwargs={'post_id': post_id})
        )
        self.assertTrue(Post.objects.filter(pk=post_id).exists())

    def test_get_request_does_not_delete(self):
        post_id = self.post.pk
        self.client.force_login(self.author)
        self.client.get(
            reverse('posts:post_delete', kwargs={'post_id': post_id})
        )
        self.assertTrue(Post.objects.filter(pk=post_id).exists())


class CacheTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='cacheuser')

    def setUp(self):
        cache.clear()

    def test_index_page_cached(self):
        Post.objects.create(author=self.user, text='Кешируемый пост')
        response1 = self.client.get(reverse('posts:index'))
        Post.objects.all().delete()
        response2 = self.client.get(reverse('posts:index'))
        self.assertEqual(response1.content, response2.content)

    def test_cache_cleared_after_post_creation(self):
        self.client.force_login(self.user)
        self.client.get(reverse('posts:index'))
        self.client.post(
            reverse('posts:post_create'),
            data={'text': 'Новый пост сбрасывает кеш'},
        )
        response = self.client.get(reverse('posts:index'))
        self.assertContains(response, 'Новый пост сбрасывает кеш')


class PaginatorTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='paguser')
        Post.objects.bulk_create([
            Post(author=cls.user, text=f'Пост {i}') for i in range(13)
        ])

    def setUp(self):
        cache.clear()

    def test_first_page_has_10_posts(self):
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_has_3_posts(self):
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)
