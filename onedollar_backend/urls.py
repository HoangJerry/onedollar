"""onedollar_backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView, TemplateView

from password_reset import views as pwd_reset_views

from onedollar import views
from onedollar import api_urls
from shopapp import urls as shopapp_urls

# merchants
from merchants import views as merchants_views
from merchants import urls as merchants_urls
from merchants import api_urls as merchants_api_urls
from django.contrib import admin

urlpatterns = [
    url(r'^admin/products/create-from-url/$', views.ProductURLCreationView.as_view(), name='producturlcreation'),
    url(r'^admin/product/(?P<pk>\d+)/bets/$', views.ProductBetsView.as_view(), name='productbets'),
    url(r'^admin/chat/$', views.ChatView.as_view(), name='chat'),
    url(r'^admin/onedollar/$', RedirectView.as_view(url=reverse_lazy('admin:index'))),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/shop/', include(shopapp_urls)),
    url(r'^api/', include(api_urls)),
    url(r'^r/(?P<code>[a-z0-9-]+)$', views.ReferralRedirect.as_view(), name='referral-link'),

    url(r'^password/recover/(?P<signature>.+)/$', pwd_reset_views.recover_done,
            name='password_reset_sent'),
    url(r'^password/reset/done/$', pwd_reset_views.reset_done, name='password_reset_done'),
    url(r'^password/reset/(?P<token>[\w:-]+)/$', pwd_reset_views.reset,
        name='password_reset_reset'),
    # merchants
    url(r'^merchants/', include(merchants_urls)),
    url(r'^api/merchants/', include(merchants_api_urls)),
    url(r'^reset-password/$', merchants_views.reset_password),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL.replace(settings.SITE_URL, ''), document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL.replace(settings.SITE_URL, ''), document_root=settings.MEDIA_ROOT)
