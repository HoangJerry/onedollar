import copy

from django.views.generic import TemplateView, RedirectView, DetailView, View
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.core.urlresolvers import reverse

import django_tables2 as tables

from models import SoldProduct, OneDollarUser, Product, Bet, Transaction

import stripe


class ProductURLCreationView(View):
    def post(self, request, *args, **kwargs):
        _product_id = request.POST.get('productId', None)

        if not _product_id:
            return HttpResponseBadRequest('INVALID_PRODUCT_ID')

        if not (request.user and request.user.is_authenticated() \
                and request.user.is_staff):
            return HttpResponseBadRequest('INVALID_USER')

        url = 'https://www.wish.com/c/'+_product_id

        product = Product.create_product_from_wish(url, request.user.id)
        
        return JsonResponse({'url': reverse('admin:onedollar_product_change', args=(product.id,))})


class BetTable(tables.Table):
    edit_link = tables.Column(accessor='user.edit_link', order_by=('user.email'))
    fblink = tables.Column(accessor='user.fblink', verbose_name='FB link', order_by=('user.fb_uid'))

    class Meta:
        model = Bet
        fields = ('number', 'edit_link', 'user.first_name', 'user.last_name', 
                'fblink', 'user.aggregated_topups', 'user.friends_count')
        attrs = {'class': 'paleblue'}


class ProductBetsView(DetailView):
    template_name = "productbets.html"
    queryset = Product.objects.all()

    def get_context_data(self, **kwargs):
        ret = super(ProductBetsView, self).get_context_data(**kwargs)

        product = self.get_object()
        bets = product.bets.all()
        table = BetTable(bets)
        tables.RequestConfig(self.request).configure(table)

        ret['table'] = table

        return ret

class ChatView(TemplateView):
    template_name = "chat.html"

    @method_decorator(staff_member_required)
    def dispatch(self, *args, **kwargs):
        return super(ChatView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        ret = super(ChatView, self).get_context_data(**kwargs)

        try:
            product_id = self.request.GET.get('product')
            ret['product'] = SoldProduct.objects.get(pk=product_id)
            ret['SITE_URL'] = settings.SITE_URL[:-1]
        except Exception as e:
            print '>>>', e
            pass
        return ret


class ReferralRedirect(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        code = kwargs.get('code', None)
        user = OneDollarUser.objects.filter(referral_code=code).first()

        if user:
            return user.get_redirect_referral_link()

        return 'http://onedollarapp.biz/'
