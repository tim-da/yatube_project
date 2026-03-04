from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from .forms import CreationForm, ProfileForm
from .models import Profile


class SignUpView(CreateView):
    form_class = CreationForm
    success_url = reverse_lazy('posts:index')
    template_name = 'users/signup.html'


@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(
        request.POST or None,
        files=request.FILES or None,
        instance=profile,
    )
    if form.is_valid():
        form.save()
        return redirect('posts:profile', username=request.user.username)
    return render(request, 'users/edit_profile.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('users:login')
