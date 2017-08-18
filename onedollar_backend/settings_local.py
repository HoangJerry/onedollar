DEBUG = True
import dj_database_url

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'onedollar',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'root',
        'PASSWORD': 'softdev',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

db_from_env = dj_database_url.config(conn_max_age=500)
DATABASES['default'].update(db_from_env)
# #SITE_URL = 'http://128.199.67.33/'
SITE_URL = 'https://dailywashbackend.herokuapp.com/'
STATIC_URL = SITE_URL + 'static/'
MEDIA_URL = SITE_URL + 'media/'


# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'file': {
#             'level': 'DEBUG',
#             'class': 'logging.FileHandler',
#             'filename': '/var/www/html/HoangTN/project/merchant-wish-django/cron_error.log',
#             # 'filename': '/var/www/html/prs/2017/merchant-wish-django/cron_error.log',
#             },
#         },
#     'loggers': {
#         'django_crontab': {
#             'handlers': ['file'],
#             'level': 'DEBUG',
#             'propagate': True,
#         },
#     },
# }