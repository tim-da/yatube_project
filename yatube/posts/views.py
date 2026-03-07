from urllib.parse import urlparse

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from users.models import Profile

from .forms import CommentForm, PostForm
from .models import Follow, Group, Like, Post

User = get_user_model()

POSTS_PER_PAGE = 10
INDEX_CACHE_TIMEOUT = 20
INDEX_CACHE_VERSION_KEY = 'index_page_cache_version'


def _get_index_cache_version():
    return cache.get(INDEX_CACHE_VERSION_KEY, 0)


def _bump_index_cache_version():
    if cache.add(INDEX_CACHE_VERSION_KEY, 1):
        return
    current_version = cache.get(INDEX_CACHE_VERSION_KEY, 0)
    cache.set(INDEX_CACHE_VERSION_KEY, current_version + 1)


def _safe_next_url(request, fallback):
    """Return referer if it's on the same host with a safe scheme, otherwise fallback."""
    referer = request.META.get('HTTP_REFERER', '')
    if referer:
        parsed = urlparse(referer)
        same_host = not parsed.netloc or parsed.netloc == request.get_host()
        safe_scheme = parsed.scheme in ('', 'http', 'https')
        if same_host and safe_scheme:
            return referer
    return fallback


def _like_context(request, page_obj):
    """Return liked_post_ids, followed_author_ids, viewer_profile for current user."""
    if not request.user.is_authenticated:
        return set(), set(), None
    post_ids = [p.pk for p in page_obj]
    author_ids = list({p.author_id for p in page_obj})
    liked_post_ids = set(
        Like.objects.filter(user=request.user, post_id__in=post_ids)
        .values_list('post_id', flat=True)
    )
    followed_author_ids = set(
        Follow.objects.filter(user=request.user, author_id__in=author_ids)
        .values_list('author_id', flat=True)
    )
    viewer_profile = Profile.objects.filter(user=request.user).first()
    return liked_post_ids, followed_author_ids, viewer_profile


def index(request):
    page_number = request.GET.get('page', '1')
    cache_version = _get_index_cache_version()
    user_key = request.user.pk if request.user.is_authenticated else 'anon'
    cache_key = f'index_post_list_v{cache_version}_p{page_number}_u{user_key}'
    posts_fragment = cache.get(cache_key)
    if posts_fragment is None:
        posts = (
            Post.objects
            .select_related('author', 'group')
            .annotate(likes_count=Count('likes'))
            .order_by('-likes_count', 'author__last_name', 'pk')
        )
        paginator = Paginator(posts, POSTS_PER_PAGE)
        page_obj = paginator.get_page(page_number)
        liked_post_ids, followed_author_ids, viewer_profile = _like_context(request, page_obj)
        posts_fragment = render_to_string(
            'posts/includes/index_post_list.html',
            {
                'page_obj': page_obj,
                'liked_post_ids': liked_post_ids,
                'followed_author_ids': followed_author_ids,
                'viewer_profile': viewer_profile,
            },
            request=request,
        )
        cache.set(cache_key, posts_fragment, INDEX_CACHE_TIMEOUT)
    return render(request, 'posts/index.html', {'posts_fragment': posts_fragment})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author').annotate(likes_count=Count('likes')).order_by('-likes_count', 'author__last_name', 'pk')
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    liked_post_ids, followed_author_ids, viewer_profile = _like_context(request, page_obj)
    return render(request, 'posts/group_list.html', {
        'group': group,
        'page_obj': page_obj,
        'liked_post_ids': liked_post_ids,
        'followed_author_ids': followed_author_ids,
        'viewer_profile': viewer_profile,
    })


def profile(request, username):
    author = get_object_or_404(User, username=username)
    author_profile = None
    try:
        author_profile = author.profile
    except Profile.DoesNotExist:
        pass
    posts = author.posts.select_related('group').annotate(likes_count=Count('likes')).order_by('-likes_count', 'pk')
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    following = (
        request.user.is_authenticated
        and Follow.objects.filter(user=request.user, author=author).exists()
    )
    liked_post_ids, followed_author_ids, viewer_profile = _like_context(request, page_obj)
    return render(request, 'posts/profile.html', {
        'author': author,
        'profile': author_profile,
        'page_obj': page_obj,
        'following': following,
        'liked_post_ids': liked_post_ids,
        'followed_author_ids': followed_author_ids,
        'viewer_profile': viewer_profile,
    })


def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.annotate(likes_count=Count('likes')),
        pk=post_id,
    )
    comments = post.comments.select_related('author')
    form = CommentForm()
    viewer_profile = None
    user_liked = False
    is_following = False
    if request.user.is_authenticated:
        viewer_profile = Profile.objects.filter(user=request.user).first()
        user_liked = Like.objects.filter(user=request.user, post=post).exists()
        is_following = (
            post.author != request.user
            and Follow.objects.filter(user=request.user, author=post.author).exists()
        )
    return render(request, 'posts/post_detail.html', {
        'post': post,
        'comments': comments,
        'form': form,
        'viewer_profile': viewer_profile,
        'user_liked': user_liked,
        'is_following': is_following,
    })


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        _bump_index_cache_version()
        return redirect('posts:profile', username=request.user.username)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if form.is_valid():
        form.save()
        _bump_index_cache_version()
        return redirect('posts:post_detail', post_id=post_id)
    return render(request, 'posts/create_post.html', {
        'form': form,
        'is_edit': True,
        'post': post,
    })


@login_required
@require_POST
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(
        author__following__user=request.user
    ).select_related('author', 'group').annotate(likes_count=Count('likes')).order_by('-likes_count', 'author__last_name', 'pk')
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    liked_post_ids, followed_author_ids, viewer_profile = _like_context(request, page_obj)
    return render(request, 'posts/follow.html', {
        'page_obj': page_obj,
        'liked_post_ids': liked_post_ids,
        'followed_author_ids': followed_author_ids,
        'viewer_profile': viewer_profile,
    })


@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)
    if request.method == 'POST':
        post.delete()
        _bump_index_cache_version()
        return redirect('posts:profile', username=request.user.username)
    return redirect('posts:post_detail', post_id=post_id)


@login_required
@require_POST
def like_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author == request.user:
        return redirect(_safe_next_url(request, f'/posts/{post_id}/'))
    changed = False
    with transaction.atomic():
        follow = Follow.objects.select_for_update().filter(
            user=request.user, author=post.author
        ).first()
        if not follow:
            return redirect(_safe_next_url(request, f'/posts/{post_id}/'))
        profile = Profile.objects.select_for_update().get(user=request.user)
        already_liked = Like.objects.filter(user=request.user, post=post).exists()
        if not already_liked and profile.stars > 0:
            try:
                Like.objects.create(user=request.user, post=post)
            except IntegrityError:
                pass
            else:
                profile.stars -= 1
                profile.save(update_fields=['stars'])
                changed = True
    if changed:
        _bump_index_cache_version()
    return redirect(_safe_next_url(request, f'/posts/{post_id}/'))


@login_required
@require_POST
def unlike_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    changed = False
    with transaction.atomic():
        profile = Profile.objects.select_for_update().get(user=request.user)
        deleted, _ = Like.objects.filter(user=request.user, post=post).delete()
        if deleted:
            profile.stars += deleted
            profile.save(update_fields=['stars'])
            changed = True
    if changed:
        _bump_index_cache_version()
    return redirect(_safe_next_url(request, f'/posts/{post_id}/'))


@login_required
@require_POST
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
@require_POST
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username=username)
