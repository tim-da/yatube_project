from django.contrib.auth import get_user_model


class PrefetchProfileMiddleware:
    """Attach authenticated user with related profile to avoid extra query in templates."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.user_model = get_user_model()

    def __call__(self, request):
        user_id = request.session.get('_auth_user_id')
        if user_id:
            try:
                request._cached_user = (
                    self.user_model.objects
                    .select_related('profile')
                    .get(pk=user_id)
                )
            except self.user_model.DoesNotExist:
                pass
        return self.get_response(request)
