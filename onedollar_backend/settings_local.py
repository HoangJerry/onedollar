DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'onedollar',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'root',
        'PASSWORD': 'softdev',
        'HOST': 'localhost',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '3306',                      # Set to empty string for default.
    }
}

#SITE_URL = 'http://128.199.67.33/'
SITE_URL = 'http://localhost:8000/'
STATIC_URL = SITE_URL + 'static/'
MEDIA_URL = SITE_URL + 'media/'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/www/html/HoangTN/project/merchant-wish-django/cron_error.log',
            # 'filename': '/var/www/html/prs/2017/merchant-wish-django/cron_error.log',
            },
        },
    'loggers': {
        'django_crontab': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}