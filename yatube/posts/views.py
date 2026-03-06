from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from users.models import Profile

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post

User = get_user_model()

POSTS_PER_PAGE = 10
INDEX_CACHE_TIMEOUT = 20
INDEX_CACHE_VERSION_KEY = 'index_page_cache_version'


def _get_index_cache_version():
    return cache.get(INDEX_CACHE_VERSION_KEY, 1)


def _bump_index_cache_version():
    if cache.add(INDEX_CACHE_VERSION_KEY, 1):
        return
    try:
        cache.incr(INDEX_CACHE_VERSION_KEY)
    except ValueError:
        current_version = cache.get(INDEX_CACHE_VERSION_KEY, 1)
        cache.set(INDEX_CACHE_VERSION_KEY, current_version + 1)


def index(request):
    page_number = request.GET.get('page', '1')
    cache_version = _get_index_cache_version()
    cache_key = f'index_post_list_v{cache_version}_p{page_number}'
    posts_fragment = cache.get(cache_key)
    if posts_fragment is None:
        posts = Post.objects.select_related('author', 'group')
        paginator = Paginator(posts, POSTS_PER_PAGE)
        page_obj = paginator.get_page(page_number)
        posts_fragment = render_to_string(
            'posts/includes/index_post_list.html',
            {'page_obj': page_obj},
            request=request,
        )
        cache.set(cache_key, posts_fragment, INDEX_CACHE_TIMEOUT)
    return render(request, 'posts/index.html', {'posts_fragment': posts_fragment})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author')
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'posts/group_list.html', {
        'group': group,
        'page_obj': page_obj,
    })


def profile(request, username):
    author = get_object_or_404(User, username=username)
    profile = None
    try:
        profile = author.profile
    except Profile.DoesNotExist:
        pass
    posts = author.posts.select_related('group')
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    following = (
        request.user.is_authenticated
        and Follow.objects.filter(user=request.user, author=author).exists()
    )
    return render(request, 'posts/profile.html', {
        'author': author,
        'profile': profile,
        'page_obj': page_obj,
        'following': following,
    })


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    comments = post.comments.select_related('author')
    form = CommentForm()
    return render(request, 'posts/post_detail.html', {
        'post': post,
        'comments': comments,
        'form': form,
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
    ).select_related('author', 'group')
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'posts/follow.html', {'page_obj': page_obj})


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
