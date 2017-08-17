import foursquare
from django.contrib import admin
from django.contrib.admin.options import csrf_protect_m
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django.utils import timezone
from django.template.defaultfilters import date as django_date_filter
from django.core.files.images import get_image_dimensions
from django.core.urlresolvers import reverse
from django.db.models import Q

from import_export import resources, fields, widgets
from import_export.admin import ExportActionModelAdmin
from import_export.formats import base_formats

from shopapp.models import Order
from merchants.models import Store
from unify_django.admin import UnifyBaseUserAdmin, BaseModelAdmin
from models import *
from constance.admin import ConstanceAdmin, ConstanceForm, Config

class CustomConfigForm(ConstanceForm):
      def __init__(self, *args, **kwargs):
        super(CustomConfigForm, self).__init__(*args, **kwargs)
        #... do stuff to make your settings form nice ...

class ConfigAdmin(ConstanceAdmin):
    change_list_form = CustomConfigForm
    change_list_template = './admin/onedollar/constance/change_list.html'

admin.site.unregister([Config])
admin.site.register([Config], ConfigAdmin)

class TransactionForm(forms.ModelForm):
    user = forms.ModelChoiceField(queryset=OneDollarUser.objects.order_by('email'))

    class Meta:
        model = Transaction
        fields = ('user', 'transaction_type', 'amount')


class TransactionResource(resources.ModelResource):
    class Meta:
        model = OneDollarUser
        fields = ('user', 'payer_firstname', 'payer_lastname', 'payer_email', 'transaction_type', 'amount', 'money', 'transaction_id', 'channel', 'creation_date')
        export_order = fields



class TransactionAdmin(ExportActionModelAdmin, admin.ModelAdmin):
    model = Transaction
    fields = ('user', 'transaction_type', 'amount',)
    search_fields = ('transaction_id', 'user__first_name', 'user__last_name', 'user__email')
    list_display = ('id', 'user_url', 'payer_firstname', 'payer_lastname', 'payer_email', 'transaction_type', 'amount', 'money', 'transaction_id', 'channel', 'creation_date')
    form = TransactionForm

    def user_url(self, obj):
        name = obj.user.get_full_name()
        name = name if len(name.strip()) > 0 else obj.user.id

        url = reverse('admin:onedollar_onedollaruser_change', args=[obj.user.id])

        return format_html(u"<a href='{url}'>{name}</a>", url=url, name=name)
    user_url.short_description = "User"

    def get_queryset(self, request):
        qs = super(TransactionAdmin, self).get_queryset(request)
        return qs.filter(transaction_type=Transaction.TYPE_TOPUP)

    def has_delete_permission(self, request, obj=None):
        return False

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['topups'] = Transaction.get_sum_topup_by_channel()
        extra_context['errors'] = Transaction.get_stripe_error_stats()
        ret = super(TransactionAdmin, self).changelist_view(request, extra_context)
        return ret


class TransactionInline(admin.TabularInline):
    model = Transaction
    fields = ('transaction_type', 'amount', 'money', 'transaction_id', 'channel', 'creation_date', 'product_link', 'use_free_credit')
    extra = 0
    readonly_fields = ('channel', 'creation_date', 'product_link', 'use_free_credit')

    def has_add_permission(self, request, obj=None):
        return True

    def product_link(self, obj):
        if not obj.bet:
            return ''

        return '<a href="{}" target="blank">{}</a>'.format(reverse('admin:onedollar_product_change', args=[obj.bet.product.id]),
                                            obj.bet.product.title)
    product_link.allow_tags = True


class OrderInline(admin.TabularInline):
    model = Order
    fields = ('action', 'amount', 'transaction_id', 'channel', 'creation_date', 'product_link')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def action(self, obj):
        return 'Buy product'
    action.allow_tags = True

    def product_link(self, obj):
        return '<a href="{}" target="blank">{}</a>'.format(reverse('admin:shopapp_product_change', args=[obj.product.id]),
                                            obj.product.title)
    product_link.allow_tags = True


class OneDollarUserResource(resources.ModelResource):
    class Meta:
        model = OneDollarUser
        fields = ('id', 'first_name', 'last_name', 'email', 'gender', 'country', 'fb_uid', 'creation_date', 'free_credits', 'credits', 'aggregated_topups', 'friends_count',)
        export_order = fields

    def dehydrate_gender(self, user):
        return user.get_gender()

    def dehydrate_country(self, user):
        return user.country.name

class MerchantInline(admin.TabularInline):
    model = Store
    fields = ('store_platform','_url_store_platform','revenue_last_year','warehouse_located',
        'warehouse_street','product_categories','provider_payment',
        'email_payment',)
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def _url_store_platform(self, obj):
        return '<a href="{}" target="blank">{}</a>'.format(obj.url_store_platform,obj.url_store_platform)
    _url_store_platform.allow_tags = True

class OneDollarUserAdmin(ExportActionModelAdmin, UnifyBaseUserAdmin):
    resource_class = OneDollarUserResource
    readonly_fields = ('credits','free_credits', 'referral_code', 'referrer')
    list_display = ('email','username','_total_amount','first_name', 'last_name', 'gender',  'platform', 'aggregated_topups', 'country', 'fblink', 'status', 'creation_date')
    list_filter = ('status', 'is_flagged', 'is_superuser', 'is_active', 'country',)
    ordering = ('-creation_date',)
    fieldsets = (
        (None, {'fields': ('status', 'email','is_email_verified', 'is_recharged', 'is_flagged', 'password')}),
        (_('Personal info'),
         {'fields': ('first_name', 'last_name', 'phone', 'street1', 'street2', 'postal_code', 
                     'province', 'city', 'avatar', 'fb_uid', 'gender',
                     'dob', 'about', 'relationship_status', 'referral_code', 'referrer')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    inlines = [MerchantInline,TransactionInline, OrderInline,]

    def __init__(self, *args, **kwargs):
        super(OneDollarUserAdmin, self).__init__(*args, **kwargs)
        self.fieldsets[1][1]['fields'] += ('credits', 'free_credits', 'country',)

    def get_export_formats(self):
        if not base_formats.XLSX().can_export():
            return super(OneDollarUserAdmin, self).get_export_formats()
        return [base_formats.XLSX]

    def fblink(self, obj):
        if obj.fb_uid:
            return '<a target="_blank" href="https://fb.com/{fb_uid}">{fb_uid}</a>'.format(fb_uid=obj.fb_uid)
        return None
    fblink.allow_tags = True

    # def get_queryset(self, request):
    # # def queryset(self, request): # For Django <1.6
    #     qs = super(OneDollarUserAdmin, self).get_queryset(request)
    #     # qs = super(CustomerAdmin, self).queryset(request) # For Django <1.6
    #     for q in qs:
    #         ret = Order.objects.filter(user=q.id).exclude(delivery_status__in=[40,60]).aggregate(sum_orders=Sum('amount'))
    #         if not ret['sum_orders']:
    #             ret['sum_orders']=0
    #         if not q.total_order == ret['sum_orders']:
    #             q.total_order = ret['sum_orders']
    #             q.save()
    #     return qs

    def _total_amount(self, obj):
        # ret = Order.objects.filter(user=obj.id).exclude(delivery_status__in=[40,60]).aggregate(sum_orders=Sum('amount'))
        # if not ret['sum_orders']:
        #     ret['sum_orders']=0
        # if not obj.total_order == ret['sum_orders']:
        #     obj.total_order = ret['sum_orders']
        #     obj.save()
        return obj.total_order
    _total_amount.short_description = "Total order"
    _total_amount.admin_order_field = "total_order"


class CategoryAdmin(BaseModelAdmin):
    list_display = ('name', 'type', 'status',)
    list_filter = ('type', 'status',)

class BrandAdmin(admin.ModelAdmin):
    list_display = ('id','name',)
    search_fields = ('name',)


class CategoryTestAdmin(admin.ModelAdmin):
    list_display = ('id','name', '_link','active','type')
    fieldsets = (
        (None, {
            'fields': ('parent', 'name','active','type')
        }),
    )

    def _link(self, obj):
        link = str(obj.get_absolute_url()).title()[1:]
        return link.replace("/", ", ")
    _link.short_description = 'Full Category'

class ProductPhotoForm(forms.ModelForm):
    class Meta:
        model = ProductPhoto
        exclude = []

    def clean_image(self):
        image = self.cleaned_data['image']

        if not image:
            raise forms.ValidationError(_("Image is required"))

        #w, h = get_image_dimensions(image)
        #if w != h:
            #raise forms.ValidationError(_("Image must be square"))

        return image


class ProductPhotoInline(admin.TabularInline):
    model = ProductPhoto
    extra = 0
    min_num = 1
    form = ProductPhotoForm


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['creator' ,'creation_date', 'status', 'is_sponsored', 
            'category', 'title', 'description', 'no_of_days', 'is_new', 'quantity', 
            'ticket_price','win_second_award','win_third_award', 'retail_price', 'location_id', 'country', 'delivery_status',
            'ordering_date', 'ordering_tracking', 'cost', 'drawing_method', 'from_shop',
            'sold_tickets', 'end_date', 'winner', 'win_number', 'location_name', 
            # 'sold_tickets', 'end_date', 'winner', 'win_number', 'win_second_number', 'win_third_number', 'location_name', 
            'location_address', 'location_city', 'location_state', 'location_country', 
            'location_lat', 'location_lng', 'payout_date', 'colors', 'sizes', 'product_quantity',
            'iteration', 'waiting_time']

    def __init__(self, *args, **kwargs):
        super(ProductAdminForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        qs = Q(is_staff=True)
        if instance:
            if hasattr(instance, 'creator') and instance.creator and not instance.creator.is_staff:
                qs = qs | Q(id=instance.creator_id)
        self.fields['category'].queryset = self.fields['category'].queryset.filter(type=Category.TYPE_BET)
        self.fields['creator'].queryset = OneDollarUser.objects.filter(qs)


class SoldProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'delivery_status', '_countries', 'days_left_to_ship', 'latest_chat_date', '_product_link', '_winner_address',
                    '_is_sponsored', 'ordering_date', 'ordering_tracking', 'from_shop', 'cost', '_open_chat_link')
    list_editable = ('delivery_status', 'ordering_date', 'ordering_tracking', 'from_shop', 'cost')
    ordering = ('-latest_chat_date',)

    def days_left_to_ship(self, obj):
        return obj.days_left_to_ship
    days_left_to_ship.admin_order_field = '_days_left_to_ship'

    def _product_link(self, obj):
        return mark_safe(obj.product_edit_url)
    _product_link.short_description = 'Product'

    def _countries(self, obj):
        return obj.countries
    _countries.allow_tags = True

    def _winner_address(self, obj):
        return mark_safe(obj.winner_full_address)
    _winner_address.short_description = "Winner"

    def _winner_second_address(self, obj):
        return mark_safe(obj.winner_second_full_address)
    _winner_second_address.short_description = "Winner 2nd"

    def _winner_third_address(self, obj):
        return mark_safe(obj.winner_third_full_address)
    _winner_third_address.short_description = "Winner 3th"

    def _is_sponsored(self, obj):
        return obj.is_sponsored
    _is_sponsored.short_description = "Spons.?"
    _is_sponsored.boolean = True

    def _open_chat_link(self, obj):
        return '<a href="{}?token={}&product={}&user={}&winner={}" target="blank">Chat</a>'.format(reverse('chat'), obj.creator.token, obj.id, obj.creator_id, obj.winner_id)
    _open_chat_link.allow_tags = True
    _open_chat_link.short_description = '' 

    def has_add_permission(self, request, obj=None):
        return False

class ProductAdmin(SoldProductAdmin):
    form = ProductAdminForm
    list_display = ('id', 'title', '_countries', 'quantity',
        'ticket_price', 'retail_price', 'category', 'is_sponsored',
        'creator', 'sold_tickets', 'end_date', 'status',
        '_winner_address', 'win_number',
        '_winner_address2', 'win_second_number',
        '_winner_address3', 'win_third_number',
         '_creation_date', 
        'product_quantity', 'iteration')
    list_editable = ()
    ordering = ('-creation_date',)
    list_filter = ('status',)
    readonly_fields = ('sold_tickets', 'end_date', 'winner', 'win_second', 'win_third', 'location_name', 'location_address', 'iteration', 
                       'location_city', 'location_state', 'location_country', 'location_lat', 'location_lng',
                       'payout_date')
    inlines = [ProductPhotoInline,]

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        formfield = super(ProductAdmin, self).formfield_for_manytomany(db_field, request=request, **kwargs)
        if db_field.name == 'country':
            formfield.help_text += ' Command or control A to select all.'
        return formfield

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

    def _winner_address2(self, obj):
        if obj.win_second:
            ret = super(ProductAdmin, self)._winner_second_address(obj)
            ret += u'<br /><a href="{}">Order and Chat</a>'.format(reverse('admin:onedollar_soldproduct_changelist'))
            ret += u'<br />'+obj.get_delivery_status_display()
            return mark_safe(ret)
        return ''
    _winner_address2.short_description = "Winner 2rd"

    def _winner_address3(self, obj):
        if obj.win_third:
            ret = super(ProductAdmin, self)._winner_third_address(obj)
            ret += u'<br /><a href="{}">Order and Chat</a>'.format(reverse('admin:onedollar_soldproduct_changelist'))
            ret += u'<br />'+obj.get_delivery_status_display()
            return mark_safe(ret)
        return ''
    _winner_address3.short_description = "Winner 3th"

    def _creation_date(self, obj):
        creation_date_str = django_date_filter(obj.creation_date, 'M j, Y, P')
        if obj.creation_date > timezone.now():
            creation_date_str = '<span style="background-color: yellow">{}</span>'.format(creation_date_str)
        return mark_safe(creation_date_str)
    _creation_date.short_description = "Creation date"

    def has_add_permission(self, request, obj=None):
        return True

    def response_change(self, request, obj):
        if '_drawwinner' in request.POST:
            obj.draw_winners()
            request.POST['_continue'] = True
            
        return super(ProductAdmin, self).response_change(request, obj)

    def save_model(self, request, obj, form, change):
        need_fsquare_data = False

        if obj.id:
            current_obj = Product.objects.get(pk=obj.id)
            if obj.location_id and obj.location_id != "" and \
                    current_obj.location_id != obj.location_id:
                need_fsquare_data = True
        else:
            need_fsquare_data = obj.location_id and obj.location_id != ""

        if need_fsquare_data:
            try:
                fsquare_client = foursquare.Foursquare(client_id=settings.FOURSQUARE_CLIENT_ID, client_secret=settings.FOURSQUARE_CLIENT_SECRET)
                ret = fsquare_client.venues(obj.location_id)
                obj.location_name = ret['venue']['name']

                location = ret['venue'].get('location', None)

                if location:
                    obj.location_address = location.get('address', '')
                    obj.location_city = location.get('city', '')
                    obj.location_state = location.get('state', '')
                    obj.location_country = location.get('country', '')
                    obj.location_lat = location.get('lat', '')
                    obj.location_lng = location.get('lng', '')
            except:
                raise forms.ValidationError(_('Invalid Foursquare ID'))

        ret = super(ProductAdmin, self).save_model(request, obj, form, change)

        obj.generate_tickets()

        return ret


class UserReportingTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'status')


class ProductReportingTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'status')


class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'currency_code', 'status')


class TopupPackageAdmin(admin.ModelAdmin):
    list_display = ('type', 'name', 'credits', 'topup_value')
    
    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    

admin.site.index_template = 'admin/index2.html'

admin.site.register(OneDollarUser, OneDollarUserAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(SoldProduct, SoldProductAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(CategoryTest, CategoryTestAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(UserReportingType, UserReportingTypeAdmin)
admin.site.register(ProductReportingType, ProductReportingTypeAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(TopupPackage, TopupPackageAdmin)
