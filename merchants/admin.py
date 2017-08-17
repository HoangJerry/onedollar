from django.contrib import admin
from models import *

# Register your models here.
from django import forms
from django.contrib import admin
from django.db.models import Q
from django.template.defaultfilters import date as django_date_filter
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse

from import_export import resources, fields, widgets
from import_export.admin import ExportActionModelAdmin
from import_export.formats import base_formats
from django.utils.translation import ugettext_lazy as _

from onedollar import models as onedollar_models
from shopapp import models as shopapp_models
from unify_django.admin import UnifyBaseUserAdmin, BaseModelAdmin

class StoreForm(forms.ModelForm):
    class Meta:
        model = Store
        exclude = ('should_display_seller_popup', 'should_display_winner_popup')

    def __init__(self, *args, **kwargs):
        super(StoreForm, self).__init__(*args, **kwargs)
    
        self.fields['user'].queryset = onedollar_models.OneDollarUser.objects.filter(is_staff=True)

class StoreAdmin(ExportActionModelAdmin, admin.ModelAdmin):
    # form = StoreForm
    list_display = ('id','_email','_storename','_country',
                    '_revenue','_pending_product','_live_product','_sold_product',
                    '_payment_history','status',)
    list_editable = ('status',)
    fieldsets = (
        ('Store info',{'fields': ('user','status','store_platform','url_store_platform',
                        'revenue_last_year','warehouse_located','warehouse_street',
                        'product_categories','provider_payment','email_payment',)}),
    )
    readonly_fields = ('user','product_categories','provider_payment','email_payment',)
    list_display_links = None

    def HoangTN_payment_history_url(self,obj):
        return '/admin/shopapp/paymenthistory/?merchant_id=%d' % (obj.user.id)

    def _payment_history(self,obj):
        return '<a href="{}" target="blank">click</a>'.format(self.HoangTN_payment_history_url(obj))
    _payment_history.allow_tags = True
    _payment_history.short_description = "Payment history"

    def HoangTN_pendding_url(self,obj):
        return '/admin/shopapp/product/?creator_id=%d&status=20' % (obj.user.id)

    def _pending_product(self,obj):
        return u"<a href='%s'>%d</a>" % (self.HoangTN_pendding_url(obj),shopapp_models.Product.objects.filter(status=shopapp_models.Product.STATUS_PENDING,creator=obj.user).count())
    _pending_product.allow_tags = True
    _pending_product.short_description = "Pending Product"

    def HoangTN_live_url(self,obj):
        return '/admin/shopapp/product/?creator_id=%d&status__in=10,30' % (obj.user.id)

    def _live_product(self,obj):
        return u"<a href='%s'>%d</a>" % (self.HoangTN_live_url(obj),shopapp_models.Product.objects.filter(status__in=[shopapp_models.Product.STATUS_APPROVED,shopapp_models.Product.STATUS_ENABLE],creator=obj.user).count())
    _live_product.allow_tags = True
    _live_product.short_description = "Live Product"

    def _sold_product(self,obj):
        temp = shopapp_models.Order.objects.exclude(delivery_status__in=[40,60]).filter(product=shopapp_models.Product.objects.filter(creator=obj.user)).aggregate(sum_orders=Sum('amount'))
        return (str(shopapp_models.Order.objects.exclude(delivery_status__in=[40,60]).filter(product=shopapp_models.Product.objects.filter(creator=obj.user)).count())+
            " / "+str(temp['sum_orders']))
    _sold_product.short_description = "Sold Product"

    def _revenue(self,obj):
        return obj.revenue_last_year
    _revenue.short_description = "Revenue"
    def _email(self, obj):
        return '<a href="{}" target="blank">{}</a>'.format(reverse('admin:onedollar_onedollaruser_change', args=[obj.user.id]),
            onedollar_models.OneDollarUser.objects.get(pk=obj.user.id).email)
    _email.allow_tags = True
    _email.short_description = "Email"

    def _storename(self, obj):
        return onedollar_models.OneDollarUser.objects.get(pk=obj.user.id).username
    _storename.short_description = "Store Name"

    def _country(self, obj):
        return onedollar_models.OneDollarUser.objects.get(pk=obj.user.id).country
    _country.short_description = "Country"

    change_list_template = './admin/store/change_list.html'
admin.site.register(Store,StoreAdmin)