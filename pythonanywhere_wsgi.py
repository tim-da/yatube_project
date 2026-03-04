# PythonAnywhere WSGI configuration file
# Copy the contents of this file into your PythonAnywhere WSGI config file.
# The WSGI config file is found at:
#   /var/www/USERNAME_pythonanywhere_com_wsgi.py
#
# Replace YOUR_USERNAME with your actual PythonAnywhere username.

import sys
import os

# Add the Django project directory to the Python path
path = '/home/YOUR_USERNAME/yatube_project/yatube'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'yatube.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
