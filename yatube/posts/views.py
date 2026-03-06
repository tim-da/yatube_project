from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm
from .models import Follow, Like, Post

User = get_user_model()


def index(request):
    posts = Post.objects.select_related('author').all()
    return render(request, 'posts/index.html', {'posts': posts})


@login_required
def post_create(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:index')
    return render(request, 'posts/create_post.html', {'form': form})


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user_liked = (
        request.user.is_authenticated
        and post.likes.filter(user=request.user).exists()
    )
    return render(request, 'posts/post_detail.html', {
        'post': post,
        'user_liked': user_liked,
    })


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    following = (
        request.user.is_authenticated
        and Follow.objects.filter(user=request.user, author=author).exists()
    )
    return render(request, 'posts/profile.html', {
        'author': author,
        'posts': posts,
        'following': following,
    })


@login_required
def follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username=username)


@require_POST
@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    profile = request.user.profile

    # Can only like posts by followed authors
    if post.author == request.user:
        return redirect('posts:post_detail', post_id=post_id)

    is_following = Follow.objects.filter(
        user=request.user, author=post.author
    ).exists()
    if not is_following:
        return redirect('posts:post_detail', post_id=post_id)

    already_liked = Like.objects.filter(user=request.user, post=post).exists()
    if not already_liked and profile.stars > 0:
        Like.objects.create(user=request.user, post=post)
        profile.stars -= 1
        profile.save()

    return redirect(request.META.get('HTTP_REFERER', 'posts:index'))


@require_POST
@login_required
def unlike_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    profile = request.user.profile

    deleted, _ = Like.objects.filter(user=request.user, post=post).delete()
    if deleted:
        profile.stars += 1
        profile.save()

    return redirect(request.META.get('HTTP_REFERER', 'posts:index'))
