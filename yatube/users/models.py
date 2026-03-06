from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    stars = models.PositiveIntegerField(default=1000)

    def __str__(self):
        return f'{self.user.username} ({self.stars} stars)'
