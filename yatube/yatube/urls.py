from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

handler403 = 'core.views.page_403'
handler404 = 'core.views.page_404'
handler500 = 'core.views.page_500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('users.urls', namespace='users')),
    path('auth/', include('django.contrib.auth.urls')),
    path('', include('posts.urls', namespace='posts')),
]

# Keep media URLs routable in environments without an external media proxy.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
