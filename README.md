# yatube_project
Социальная сеть для блогеров

## Production environment variables

Set these before running in production (note the `DJANGO_` prefix):

```bash
export DJANGO_DEBUG=false
export DJANGO_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')"
export DJANGO_ALLOWED_HOSTS="example.com,www.example.com"
export DJANGO_SECURE_SSL_REDIRECT=true
export DJANGO_SECURE_HSTS_SECONDS=31536000
export DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=true
export DJANGO_SECURE_HSTS_PRELOAD=true
```
