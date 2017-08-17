from django.conf.urls import include, url
from rest_framework.routers import DefaultRouter

import api as api_views
import models

router = DefaultRouter()
router.register(r'products', api_views.ProductViewSet)
router.register(r'orders', api_views.OrderViewSet)

urlpatterns = router.urls

urlpatterns += [
    url(r'^backend/stats/$', api_views.BackendStats.as_view(), name="backend-stats"),
    url(r'^categories/$', api_views.CategoryList.as_view(), name='categories-list'),
    # url(r'^backend/category/$', api_views.BackendCategory.as_view(), name="backend-stats"),
    url(r'^check-before-topup/$', api_views.CheckBeforeTopUp.as_view(), name="check-before-topup"),
    url(r'^products/(?P<pk>[0-9]+)/sister$', api_views.Sister.as_view(), name='sister'),
    url(r'^get/(?P<pk>(\d+(?:\.\d+)?)+)/dollars/$', api_views.GetDollar.as_view(), name='dollars'),
    url(r'^product/create/$', api_views.ProductCreate.as_view(), name='email-new-order'),
    url(r'^product/me/$', api_views.ProductMe.as_view(), name='email-new-order'),
    url(r'^product/update/unique/$', api_views.ProductUpdateUniques.as_view(), name='email-new-order'),
    url(r'^product/check/unique/$', api_views.ProductCheckUnique.as_view(), name='email-new-order'),
    url(r'^product/update/status/$', api_views.ProductUpdateStatusByMerchant.as_view(), name='email-new-order'),
    url(r'^product/me/(?P<pk>[0-9]+)/$', api_views.ProductRetrieveUpdateDestroy.as_view(), name='email-new-order'),
    url(r'^order/me/$', api_views.OrderMe.as_view(), name='email-new-order'),
    url(r'^payment/me/$', api_views.PaymentHistory.as_view(), name='email-new-order'),
    url(r'^payment/me/detail/$', api_views.PaymentDetail.as_view(), name='email-new-order'),
    url(r'^payment/me/status/$', api_views.PaymentStatus.as_view(), name='email-new-order'),
    url(r'^order/tracking/$', api_views.UpdateTracking.as_view(), name='update-tracking'),
    url(r'^order/refund/$', api_views.RefundOrder.as_view(), name='update-tracking'),
    url(r'^export/order/csv/$', api_views.export_order_csv, name='export_order_csv'),
    url(r'^export/product/csv/$', api_views.export_product_csv, name='export_order_csv'),
    url(r'^export/order/xls/$', api_views.export_order_xls, name='export_order_xls'),
    url(r'^export/product/xls/$', api_views.export_product_xls, name='export_order_xls'),
    url(r'^check/$', api_views.PaymentMerchant, name='export_order_xls'),
    url(r'^check/decode/$', api_views.Decode, name='export_order_xls'),
    url(r'^check/hack/$', api_views.HackOrder.as_view(), name='export_order_xls'),
]
