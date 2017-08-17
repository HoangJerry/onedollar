from django import forms
from django.contrib import admin
from django.db.models import Q
from django.template.defaultfilters import date as django_date_filter
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter

from django.utils import timezone
from django.utils.safestring import mark_safe

from import_export import resources, fields, widgets
from import_export.admin import ExportActionModelAdmin
from import_export.formats import base_formats

from onedollar.models import Category, OneDollarUser
from merchants.models import Store
from merchants import api as merchants_api
from .models import *

class ProductPhotoInline(admin.TabularInline):
    model = ProductPhoto
    extra = 0
    min_num = 1


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        exclude = ('should_display_seller_popup', 'should_display_winner_popup')

    def __init__(self, *args, **kwargs):
        super(ProductAdminForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        qs = Q(is_staff=True)
        if instance:
            if hasattr(instance, 'creator') and instance.creator and not instance.creator.is_staff:
                qs = qs | Q(id=instance.creator_id)
        self.fields['category'].queryset = self.fields['category'].queryset.filter(type=CategoryTest.TYPE_SHOP)
        self.fields['creator'].queryset = OneDollarUser.objects.exclude(is_staff=False).filter(qs)
        self.fields['product_parent'].queryset = self.fields['product_parent'].queryset.filter(category=CategoryTest.objects.filter(name='COMBO'))

class UniqueForm(forms.ModelForm):
    class Meta:
        model = Unique
        exclude = []

def ApprovalProduct(modeladmin, request, queryset):
    queryset.update(status=Product.STATUS_APPROVED)
    for q in queryset: 
        merchants_api.SendProductAprrovedEmail(product=q.title,creator=q.creator.id)
ApprovalProduct.short_description = "Approval"

class ProductUniqueForm(admin.TabularInline):
    model = Unique
    extra = 0
    min_num = 1
    form = UniqueForm
    readonly_fields =('unique_id','size','color','quantity','product_sold',)
    def has_add_permission(self, request, obj=None):
        return False

class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('id', 'title','_product_parent','_countries', 'quantity', 'retail_price', 'buying_price', 'reward_tokens', 'category', '_creator', '_creation_date', 'status',)
    inlines = (ProductPhotoInline,ProductUniqueForm)
    actions = [ApprovalProduct,]

    list_editable = ('status',)
    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        formfield = super(ProductAdmin, self).formfield_for_manytomany(db_field, request=request, **kwargs)
        if db_field.name == 'country':
            formfield.help_text += ' Command or control A to select all.'
        return formfield
    
    def _product_parent(self, obj):
        return obj.parents
    _product_parent.short_description = "Parent"

    def _creator(self, obj):
        if obj.creator.is_staff and obj.creator.is_superuser:
            return obj.creator
        return str(obj.creator.username) + str(' - ') + str(obj.creator)
    _creator.short_description = "Creator"

    def _countries(self, obj):
        return obj.countries
    _countries.allow_tags = True

    def _winner_address(self, obj):
        if obj.winner:
            ret = super(ProductAdmin, self)._winner_address(obj)
            ret += u'<br /><a href="{}">Order and Chat</a>'.format(reverse('admin:onedollar_soldproduct_changelist'))
            ret += u'<br />'+obj.get_delivery_status_display()
            return mark_safe(ret)
        return ''
    _winner_address.short_description = "Winner"

    def _creation_date(self, obj):
        creation_date_str = django_date_filter(obj.creation_date, 'M j, Y, P')
        if obj.creation_date > timezone.now():
            creation_date_str = '<span style="background-color: yellow">{}</span>'.format(creation_date_str)
        return mark_safe(creation_date_str)
    _creation_date.short_description = "Creation date"

    change_form_template = './admin/product/change_form.html'

class OrderResource(resources.ModelResource):
    class Meta:
        model = Order
        fields = ('product', 'user', 'amount', 'reward_tokens', 'transaction_id', 
            'payer_firstname', 'payer_lastname', 'payer_email', 'channel', 'creation_date',)
        export_order = fields

    def dehydrate_channel(self, order):
        return order.get_channel_display()

class OrderAdmin(ExportActionModelAdmin, admin.ModelAdmin):
    resource_class = OrderResource
    search_fields = ('transaction_id', 'user__first_name', 'user__last_name', 'user__email')
    list_display = ('product', '_userlink','amount', 'reward_tokens', 'transaction_id', 
        'payer_firstname', 'payer_lastname', 'payer_email', 'channel', 'creation_date',
        'variation','delivery_status',)
    list_filter = ('creation_date','delivery_status',('product__creator',RelatedDropdownFilter),)
    list_per_page = 20
    readonly_fields = ('is_payment_on',)
    fieldsets = (
        (None, {
            'fields': ('product', 'amount', 'channel', 'transaction_code', 'transaction_id', 
                'payer_firstname', 'payer_lastname', 'payer_email','is_payment_on'),
        }),
        (u'Shipping info', {
            'fields': ('firstname', 'lastname', 'email', 'phone', 'street1', 'street2', 
                'postal_code', 'province', 'city', 'country', 'delivery_status', 'shipping_time', 
                'tracking_number',),
        }),
    )

    def _userlink(self, obj):
        return obj.user.edit_link
    _userlink.short_description = "User"
    change_form_template = './admin/order/change_form.html'

class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('id','_merchant','_payment_history','total_amount','status',
                'transaction_id')
    search_fields = ('payment_history','merchant__first_name','merchant__last_name',)
    list_filter = ('status',)
    list_per_page = 50
    def HoangTN_payment_detail_url(self,obj):
        return '/admin/shopapp/order/?delivery_status=20&is_payment_on=%s&product__creator__id=%d' % (obj.payment_history,obj.merchant.id)


    def _payment_history(self,obj):
        return '<a href="{}" target="blank">{}</a>'.format(self.HoangTN_payment_detail_url(obj),obj.payment_history)
    _payment_history.allow_tags = True
    _payment_history.short_description = "Payment history"

    def _merchant(self,obj):
        return obj.merchant.username
    _merchant.short_description = "Merchant"

    def has_add_permission(self, request, obj=None):
        return False


admin.site.register(PaymentHistory, PaymentHistoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Order, OrderAdmin)

