from django.conf.urls import include, url

import views

urlpatterns = [
    # WEB VIEW
    url(r'^$', views.index, name='index'),
    url(r'^welcome/$', views.welcome, name='welcome'),
    url(r'^login/$', views.login, name='login'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^register/$', views.register, name='register'),
    url(r'^register/step2/$', views.register_step2, name='register_step2'),
    url(r'^register/step3/$', views.register_step3, name='register_step3'),
    url(r'^forget_password/$', views.forget_password, name='forget_password'),
    url(r'^account-validated/$', views.account_validated, name='account-validated'),
    url(r'^request-confirmation-by-phone/$', views.request_confirmation_by_phone, name='request_confirmation_by_phone'),
    url(r'^terms-of-service/$', views.terms_of_service, name='terms_of_service'),
    url(r'^payment-settings/$', views.payment_settings, name='payment_settings'),
    url(r'^add-products/$', views.add_products, name='add_products'),
    url(r'^edit-products/$', views.edit_products, name='edit_products'),
    url(r'^product/$', views.product, name='product'),
    url(r'^order/history/$', views.order_history, name='order_history'),
    url(r'^payment-history/$', views.payment_history, name='payment_history'),

    # Account setting
    url(r'^settings/email-preferences/$', views.email_preferences, name='email_preferences'),
    url(r'^settings/general-information/$', views.general_information, name='general_information'),
    url(r'^settings/display-settings/$', views.display_settings, name='display_settings'),
    url(r'^settings/change-username/$', views.change_username, name='change_username'),
    url(r'^settings/change-password/$', views.change_password, name='change_password'),
    url(r'^settings/change-email/$', views.change_email, name='change_email'),
    
]