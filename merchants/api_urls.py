from django.conf.urls import include, url

import api as api_views

urlpatterns = [
    url(r'^$', api_views.api_root),
    url(r'^me/$', api_views.StoreDetail.as_view(), name='merchants-detail'),
    url(r'^phone/send/$', api_views.PhoneSendSms.as_view(), name='phone-send-sms'),
    url(r'^phone/verify/$', api_views.PhoneVerify.as_view(), name='phone-verify-sms'),
    url(r'^email/status/$', api_views.EmailStatus.as_view(), name='email-status'),
    url(r'^me/term-verify/$', api_views.Term.as_view(), name='term-verify'),
    url(r'^me/change/username/$', api_views.ChangeUserName.as_view(), name='change-username'),
    url(r'^me/change/password/$', api_views.ChangePassword.as_view(), name='change-password'),
    url(r'^me/change/email/$', api_views.ChangeEmail.as_view(), name='change-email'),
    url(r'^me/email/openshop/$', api_views.SendOpenStoreEmail.as_view(), name='email-shop'),
    url(r'^me/email/new-order/$', api_views.SendRequestOrderEmail.as_view(), name='email-new-order'),

]
