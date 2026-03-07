from django.contrib.auth.views import LoginView
from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path(
        'login/',
        LoginView.as_view(template_name='users/login.html'),
        name='login',
    ),
    path(
        'logout/', views.logout_view, name='logout'
    ),
    path('edit/', views.edit_profile, name='edit_profile'),
]
