from django.conf import settings
from django.db.models import F, Sum, Count
from django.utils import timezone
import datetime as dt
import calendar
from django.db.models import Q, F, Count, Expression
from constance import config

from rest_framework import viewsets, mixins, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from unify_django import api_utils
from merchants import models as merchant_models
from merchants.api import SendPaymentHistoryEmail
from onedollar import payment as onedollar_payment, models as onedollar_models
from onedollar_backend.settings_local import MEDIA_URL
from unify_django.permissions import IsOwnerOrReadOnly
from unify_django import api_utils

import models
import serializers
import random

import csv
import xlwt
import ast
import categories
from django.http import HttpResponse
from onedollar import tasks

def export_order_csv(request):
    permission_classes = [permissions.IsAuthenticated]
    user = request.user
    response = HttpResponse(content_type='text/csv')
    name = "Order-{}.csv".format(dt.datetime.now())
    response['Content-Disposition'] = 'attachment; filename = '+name

    writer = csv.writer(response)
    writer.writerow(['product','user','amount','reward_tokens','transaction_id','payer_firstname',
    'payer_lastname','payer_email',])
    orders = models.Order.objects.filter(product__creator=user).values_list('product','user','amount','reward_tokens','transaction_id','payer_firstname',
    'payer_lastname','payer_email',)
    for order in orders:
        writer.writerow(order)

    return response

def export_product_csv(request):
    permission_classes = [permissions.IsAuthenticated]
    user = request.user
    response = HttpResponse(content_type='text/csv')
    name = "Product-{}.csv".format(dt.datetime.now())
    response['Content-Disposition'] = 'attachment; filename = '+name

    writer = csv.writer(response)
    writer.writerow(['Product ID','Product Name','SKU','Price','Shipping','Last Update','Date Uploaded',])

    products = models.Product.objects.filter(creator=user).values_list('pk','title','unique_id','buying_price','shipping_cost',
        'creation_date','modification_date',)
    for product in products:
        writer.writerow(product)

    return response

def export_order_xls(request):
    permission_classes = [permissions.IsAuthenticated]
    user = request.user
    response = HttpResponse(content_type='text/csv')
    name = "Order-{}.xls".format(dt.datetime.now())
    response['Content-Disposition'] = 'attachment; filename = '+name

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Order')

    # Sheet header, first row
    row_num = 0

    font_style = xlwt.XFStyle()
    font_style.font.bold = True
     

    columns = ['product','user','amount','reward_tokens','transaction_id','payer_firstname',
    'payer_lastname','payer_email',]

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()

    rows = models.Order.objects.filter(product__creator=user).values_list('product','user','amount','reward_tokens',
        'transaction_id','payer_firstname','payer_lastname','payer_email',)
    twips_per_row = 255 #default row height for 10 point font 
    ws.col(4).width = int(40*twips_per_row) 
    ws.col(7).width = int(30*twips_per_row)
    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            ws.write(row_num, col_num, row[col_num], font_style)

    wb.save(response)
    return response

def export_product_xls(request):
    permission_classes = [permissions.IsAuthenticated]
    user = request.user
    response = HttpResponse(content_type='text/csv')
    name = "Product-{}.xls".format(dt.datetime.now())
    response['Content-Disposition'] = 'attachment; filename = '+name

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Product')

    # Sheet header, first row
    row_num = 0

    font_style = xlwt.XFStyle()
    font_style.font.bold = True
     

    columns = ['Product ID','Product Name','SKU','Price','Shipping',]

    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()

    rows = models.Product.objects.filter(creator=user).values_list('pk','title','unique_id','buying_price','shipping_cost',)
    twips_per_row = 255 #default row height for 10 point font 
    ws.col(1).width = int(25*twips_per_row) 
    # ws.col(7).width = int(30*twips_per_row)
    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            ws.write(row_num, col_num, row[col_num], font_style)

    wb.save(response)
    return response


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    # queryset = models.Product.showable.order_by('-creation_date')
    queryset = models.Product.objects.filter(Q(status=models.Product.STATUS_ENABLE)|Q(status=models.Product.STATUS_APPROVED)).order_by('-creation_date')

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.ProductListSerializer
        return serializers.ProductCreateSerializer

class ProductCreate(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.ProductCreateSerializer
    
    def post(self,request,format=None):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        user.is_create_product=True
        user.save()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data['creator']=user
        serializer.validated_data['shipping_time']=request.data.get('shipping_time')
        print serializer.initial_data
        print serializer.validated_data
        serializer.create(serializer.validated_data,user)
        return Response('success')

class ProductUpdateUniques(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.UniquesUpdateSerializer
    
    def post(self,request,format=None):
        # user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
 
        uniques = serializer.initial_data.getlist('uniques')
        for unique in uniques:
            temp = ast.literal_eval(unique)
            models.Unique.objects.filter(unique_id = temp['unique_id'],product=temp['product_id']).update(quantity=temp['quantity'],
                buying_price=temp['buying_price'],shipping_cost=temp['shipping_cost'])
        return Response('success')

class ProductCheckUnique(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self,request,format=None):
        if models.Product.objects.filter(unique_id=request.data.get('unique_id')):
            return Response(0)
        return Response(1)

class ProductUpdateStatusByMerchant(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self,request,format=None):
        # user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        status_destination = request.data.get('status')
        if status_destination==str(models.Product.STATUS_ENABLE):
            status_destination=models.Product.STATUS_PENDING
        if status_destination==str(models.Product.STATUS_APPROVED):
            status_destination=models.Product.STATUS_PENDING
        models.Product.objects.filter(id=request.data.get('product_id')).update(status=status_destination)
        return Response('Product has change status to {}'.format(status_destination))

class ProductRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = serializers.ProductCreateSerializer
    queryset = models.Product.objects.all()
    permission_classes = (IsOwnerOrReadOnly,)

class UpdateTracking(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def add_months(self,sourcedate,months):
        month = sourcedate.month - 1 + months
        year = int(sourcedate.year + month / 12 )
        month = month % 12 + 1
        day = min(sourcedate.day,calendar.monthrange(year,month)[1])
        return dt.date(year,month,day)

    def payment_create(self,obj):
        now = dt.date.today()
        title = now
        if title.day>=16 and title.day<=31:
            last_title = title.replace(day=16)
            title = title.replace(day=1)
            title = add_months(title,1)
        else:
            title = title.replace(day=16)
            last_title = title.replace(day=1)

        now = title
        title = title.strftime("%Y-%m-%d")
        last_title = last_title.strftime("%Y-%m-%d")
        user = obj.product.creator

        if not obj.is_payment_on:
            if not models.PaymentHistory.objects.filter(merchant=user, payment_history=title):
                x = models.PaymentHistory(merchant=user,payment_history=title,total_amount=obj.amount*0.8)
                x.save()
            else:
                x = models.PaymentHistory.objects.get(merchant=user,payment_history=title)
                if x.status==models.PaymentHistory.STATUS_UPCOMING:
                    x.total_amount = x.total_amount+obj.amount*0.8
                    x.save()
            obj.is_payment_on=now
            obj.save()

    def post(self,request,format=None):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        order = models.Order.objects.get(id=request.data.get('order_id'))
        if request.data.get('tracking_number'):
            order.tracking_number = request.data.get('tracking_number')
        if request.data.get('note_yourself'):
            order.note_yourself = request.data.get('note_yourself')
        if not order.is_payment_on:
            self.payment_create(order)
        order.delivery_status = models.Order.DELIVERY_STATUS_SHIPPED
        order.save()
        return Response("success")


class RefundOrder(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self,request,format=None):

        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        print request.data.get('order_id')
        order = models.Order.objects.get(id=request.data.get('order_id'))
        now = dt.date.today()
        if order.is_payment_on<=now:
            raise api_utils.BadRequest('THIS_ORDER_HAS_BEEN_PAYMENTED_FOR_MERCHANT')
        if not order.delivery_status == models.Order.DELIVERY_STATUS_NOTSENT and not order.delivery_status == models.Order.DELIVERY_STATUS_NOTSENTADMIN:
            tasks.refund_paypal(order.transaction_id)
        # tasks.refund_paypal('4C545361SW1174339')
            order.delivery_status = models.Order.DELIVERY_STATUS_NOTSENT
            if user.is_superuser:
                order.delivery_status = models.Order.DELIVERY_STATUS_NOTSENTADMIN
            order.user.total_order = order.user.total_order - order.amount
            order.user.save()
            order.save()
        return Response("success")


class ProductMe(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.ProductSerializer
    
    def get_queryset(self):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        ret = models.Product.objects.filter(creator=user)

        search_query = self.request.GET.get('search_id', None)
        if search_query:
            ret = ret.filter(id__icontains=search_query)
        search_query = self.request.GET.get('search_name', None)
        if search_query:
            ret = ret.filter(title__icontains=search_query)
        search_query = self.request.GET.get('search_sku', None)
        if search_query:
            ret = ret.filter(unique_id__icontains=search_query)

        status__in = self.request.GET.get('status__in', None)

        if status__in:
            status__in = status__in.split(",")
            ret = ret.filter(status__in=status__in)
        return ret
        
class ProductRelative(APIView):
    permission_classes = (permissions.IsAuthenticated,)

class OrderMe(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.OrderSerializer

    def get_queryset(self):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        ret = models.Order.objects.filter(product__creator=user)

        search_query = self.request.GET.get('search_id', None)
        if search_query:
            ret = ret.filter(id__icontains=search_query)
        search_query = self.request.GET.get('search_name', None)
        if search_query:
            ret = ret.filter(product__title__icontains=search_query)
        search_query = self.request.GET.get('search_sku', None)
        if search_query:
            ret = ret.filter(product__unique_id__icontains=search_query)
        search_query = self.request.GET.get('search_tracking', None)
        if search_query:
            ret = ret.filter(tracking_number__icontains=search_query)
        
        return ret
        


class OrderViewSet(mixins.CreateModelMixin,
                          mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    queryset = models.Order.objects.order_by('-creation_date')
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.OrderSerializer


    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        free_item = self.request.data.get('free_item',None)
        if free_item:
            product = models.Product.objects.get(id=free_item)
        # product = models.Product.showable.filter(
        #         pk=self.request.data.get('free_item', 0)).first()
        validated_data = {}
        validated_data['amount'] = 0
        validated_data['reward_tokens'] = 0
        validated_data['channel'] = models.Order.CHANNEL_PAYPAL
        
        if not free_item:
            paypal_id = self.request.data.get('paypal_id', None)
            stripe_token = self.request.data.get('stripe_token', None)
            google_pay_token = self.request.data.get('google_pay_token', None)
            google_pay_purchaseToken = self.request.data.get('purchaseToken', None)
            product = models.Product.objects.get(id=self.request.data.get('product', 0))
            # product = models.Product.showable.filter(
            #     pk=self.request.data.get('product', 0)).first()

            unique_id = models.Unique.objects.filter(unique_id=self.request.data.get('unique_id',None),product = product).first()
            buying_price = product.buying_price
            if unique_id:
                validated_data['variation'] = unique_id.unique_id
                unique_id.product_sold = unique_id.product_sold + 1
                unique_id.quantity = unique_id.quantity -1
                unique_id.save()
                buying_price = unique_id.buying_price
            print buying_price

            if not paypal_id and not stripe_token and not google_pay_token:
                raise api_utils.BadRequest('INVALID_PAYMENT_DATA')
            elif paypal_id:
                if onedollar_models.Transaction.objects.filter(paypal_id=paypal_id).first() or \
                    models.Order.objects.filter(transaction_code=paypal_id).first():
                    raise api_utils.BadRequest('PAYPAL_ID_EXISTS')

                paypal = onedollar_payment.PayPalPayment(
                    mode=settings.PAYPAL_MODE,
                    client_id=settings.PAYPAL_CLIENT_ID,
                    client_secret=settings.PAYPAL_CLIENT_SECRET
                )

                receipt_data = paypal.verify_receipt(paypal_id)
                transaction = receipt_data['transactions'][0]
                related_resource = transaction['related_resources'][0]
                payer = receipt_data['payer']['payer_info']

                amount = transaction['amount']
                amount = int(float(amount['total']))
                # return Response({"product":"product.id"})
                if amount != (buying_price+product.shipping_cost):
                    raise api_utils.BadRequest('PAYPAL_INVALID_AMOUNT')

                validated_data['amount'] = amount
                validated_data['transaction_id'] = related_resource['sale']['id']
                validated_data['transaction_code'] = paypal_id
                validated_data['channel'] = models.Order.CHANNEL_PAYPAL

                if payer:
                    validated_data['payer_firstname'] = payer['first_name']
                    validated_data['payer_lastname'] = payer['last_name']
                    validated_data['payer_email'] = payer['email']
            elif stripe_token:
                try:
                    stripe_payment = payment.StripePayment()

                    amount = int(product.buying_price*100)
                    currency = self.request.user.country.currency_code

                    stripe_payment = payment.StripePayment()
                    charge = stripe_payment.charge(amount=amount, currency=currency, token=stripe_token)
                    
                    validated_data['transaction_code'] = stripe_token
                    validated_data['transaction_id'] = charge.id
                    validated_data['amount'] = amount/100
                    validated_data['channel'] = models.Order.CHANNEL_STRIPE
                except payment.StripePayment.StripePaymentException:
                    raise api_utils.BadRequest('STRIPE_ERROR')
                except Exception as e:
                    raise api_utils.BadRequest(e.message)
            elif google_pay_token:
                raise api_utils.BadRequest("NOT SUPPORT")
                # try:
                #     amount = int(product.buying_price+product.shipping_cost)

                #     validated_data['transaction_code'] = google_pay_purchaseToken
                #     validated_data['transaction_id'] = google_pay_token
                #     validated_data['amount'] = amount
                #     validated_data['channel'] = models.Order.CHANNEL_GOOGLE_PAY
                # except Exception as e:
                    # raise api_utils.BadRequest(e.message)

            validated_data['reward_tokens'] = product.reward_tokens
            self.request.user.credits = F('credits') + product.reward_tokens
            self.request.user.total_order = F('total_order') + amount
            self.request.user.is_recharged=True
            self.request.user.save()

        validated_data['shipping_time'] = product.shipping_time
        validated_data['firstname'] = self.request.user.first_name
        validated_data['lastname'] = self.request.user.last_name
        validated_data['city'] = self.request.user.city
        validated_data['country_id'] = self.request.user.country_id
        validated_data['email'] = self.request.user.email
        validated_data['phone'] = self.request.user.phone
        validated_data['postal_code'] = self.request.user.postal_code
        validated_data['province'] = self.request.user.province
        validated_data['street1'] = self.request.user.street1
        validated_data['street2'] = self.request.user.street2

        serializer.save(user=self.request.user, **validated_data)


class BackendStats(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        if not request.user.is_staff:
            raise api_utils.BadRequest('REQUIRE_IS_STAFF')

        ret = {}

        try:
            ret = models.Order.get_sum_all_orders()
            ret['count_products'] = models.Product.objects.filter(Q(status=models.Product.STATUS_APPROVED)|Q(status=models.Product.STATUS_ENABLE)).count()
            ret['count_pending'] = models.Product.objects.filter(status=models.Product.STATUS_PENDING).count()
        except:
            pass

        return Response(ret)

# class BackendCategory(generics.ListAPIView):
#     permission_classes = (permissions.IsAuthenticated,)
#     serializer_class = CategoryNewSerializer

#     def get_queryset(self):
#         category_id = self.request.GET.get('id',0)
#         return onedollar_models.CategoryNew.objects.filter(category=category_id)

class CategoryList(generics.ListAPIView):
    serializer_class = serializers.CategorySerializer
    queryset = categories.models.Category.objects.all()

class CheckBeforeTopUp(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        user_id = request.user.id

        ret = {}

        try:
            start_date = timezone.now().date()
            end_date = start_date + dt.timedelta( days=1 )
            numPerDay = models.Order.objects.filter(creation_date__range=(start_date, end_date), user_id = user_id).exclude(amount = 0).count()
            
            ret['status'] = 0
            if (numPerDay >= config.LIMIT_NUMBER_OF_PAYMENT_PER_DAY):
                ret['message'] = "Limit number of payment per day"
                request.user.is_flagged = True
            else:
                start_date2 = timezone.now().date() + dt.timedelta( days=1 )
                end_date2 = start_date2 - dt.timedelta( days=8 )
                orderPerWeek = models.Order.objects.filter(creation_date__range=(end_date2, start_date2), user_id = user_id)
                amountPerWeek = 0
                for objOrder in orderPerWeek:
                    amountPerWeek += objOrder.amount
                if (amountPerWeek >= config.LIMIT_AMOUT_OF_PAYMENT_PER_WEEK):
                    ret['message'] = "Limit amount of payment per week"
                    request.user.is_flagged = True
                else:
                    ret['status'] = 1
                    request.user.is_flagged = False
            request.user.save()
        except:
            pass
        return Response(ret)

class Sister(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        sisters=models.Product.objects.filter(Q(Q(orders_count__lte=F('quantity')) | Q(quantity=None), product_parent__id=pk))
        data = []
        i=0
        numPro=2
        for sister in sisters:
            i=i+1
            item = {}
            count = models.Order.objects.filter(product=sister).count()
            photo=models.ProductPhoto.objects.filter(product=sister)[0]
            item["count"] = count
            item["id"]=sister.id
            item["title"]=sister.title
            item["photo"]=MEDIA_URL + str(photo.image)
            data.append(item)
            if i>numPro: break
        ret = {}
        ret['status']='fail'
        ret['data']=data
        if models.CoinCount.objects.filter(count_for = models.CoinCount.COUNT_COIN_SWAP):
            countSwap = models.CoinCount.objects.get(count_for = models.CoinCount.COUNT_COIN_SWAP)
            ret['count_swap'] = countSwap.count
        else:
            ret['count_swap'] = 0
        if data:
            # user_id = request.user.id
            # user = onedollar_models.OneDollarUser.objects.get(pk=user_id)
            # user.receive_bonus=True
            # user.save()
            ret['status']='succsess'
        return Response(ret)   

class GetDollar(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        user_id = request.user.id
        user = onedollar_models.OneDollarUser.objects.get(pk=user_id)
        # user.receive_bonus=False
        ret = {}
        if float(pk)<=2:
            # trans = onedollar_models.Transaction(user=user,transaction_type=onedollar_models.Transaction.TYPE_REWARD,amount=pk)
            # trans.save()
            if float(pk)==2:
                if models.CoinCount.objects.filter(count_for = models.CoinCount.COUNT_COIN_SWAP):
                    x=models.CoinCount.objects.get(count_for = models.CoinCount.COUNT_COIN_SWAP)
                    x.count=x.count+1
                    x.save()
                    y=models.Order.objects.filter(user_id=user_id).last()
                    y.reward_tokens = F('reward_tokens')+2
                    y.save()
                else:
                    x = models.CoinCount()
                    x.count_for=models.CoinCount.COUNT_COIN_SWAP
                    x.count=1
                    x.save()
                    y=models.Order.objects.filter(user_id=user_id).last()
                    y.reward_tokens = F('reward_tokens')+2
                    y.save()
            user.credits = user.credits+float(pk)
            user.save()
            ret['status']='succsess'
        else:
            ret['status']='fail'
        # print user.credits
        return Response(ret)

class PaymentHistory(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.PaymentHistorySerializer

    def get_queryset(self):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        ret = models.PaymentHistory.objects.filter(merchant=user)
        query = self.request.GET.get('status',None)
        if query:
            ret = ret.filter(status=query)
        return ret

class PaymentDetail(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.OrderSerializer

    def get_queryset(self):
        # ret = models.Order.objects.order_by('user').distinct('user').exclude(delivery_status__in=[40,60]).aggregate(sum_orders=Sum('amount'))

        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        
        date = self.request.GET.get('date', None)
        title = dt.datetime.strptime(date,"%Y-%m-%d")

        ret = models.Order.objects.filter(product__creator=user,is_payment_on=title,delivery_status=20)
        return ret

class PaymentStatus(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self,request,format=None):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        ret = {}
        ret['upcoming'] = models.PaymentHistory.objects.filter(merchant=user,status=0).count()
        ret['pending'] = models.PaymentHistory.objects.filter(merchant=user,status=10).count()
        ret['completed'] = models.PaymentHistory.objects.filter(merchant=user,status=20).count()
        return Response(ret)

def PaymentMerchant(request):
    # now = '2017-08-16'
    now = dt.date.today()
    payments = models.PaymentHistory.objects.filter(Q(payment_history=now,status=models.PaymentHistory.STATUS_UPCOMING)|Q(status=models.PaymentHistory.STATUS_PENDING))
    paypal = onedollar_payment.PayPalPayment(
                    mode=settings.PAYPAL_MODE,
                    client_id=settings.PAYPAL_CLIENT_ID,
                    client_secret=settings.PAYPAL_CLIENT_SECRET
                ) 

    for payment in payments:
        pay=[]
        merchant = merchant_models.Store.objects.filter(user=payment.merchant).first()
        if merchant.provider_payment == merchant_models.Store.CHANNEL_PAYPAL:
            item = {
                "recipient_type": "EMAIL",
                "amount": {
                    "value": payment.total_amount,
                    "currency": "USD"
                },
                "receiver": merchant.email_payment,
                "note": "Payment of {}".format(payment.payment_history),
                "sender_item_id": "{}_{}".format(merchant.user.id,payment.payment_history)
            }
            pay.append(item)
            print pay   
            do=paypal.pay_for_merchant(pay)
            if do:
                payment.status=models.PaymentHistory.STATUS_COMPLETED
                payment.payout_item_id = do
                payment.transaction_id = 'Paypal-'
                payment.save()
                #Send email
                SendPaymentHistoryEmail(merchant.user,payment.payment_history)
            else:
                payment.status=models.PaymentHistory.STATUS_PENDING
                payment.save()
        elif merchant.provider_payment == merchant_models.Store.CHANNEL_PAYONEER:
            payment.status=models.PaymentHistory.STATUS_PENDING
            payment.save()

def Decode(request):
    paypal = onedollar_payment.PayPalPayment(
                    mode=settings.PAYPAL_MODE,
                    client_id=settings.PAYPAL_CLIENT_ID,
                    client_secret=settings.PAYPAL_CLIENT_SECRET
                ) 
    payments = models.PaymentHistory.objects.filter(payment_history='2017-08-16')
    
    for payment in payments:
        no = paypal.decode_transaction(payment.payout_item_id)
        if no:
            payment.transaction_id=payment.transaction_id+str(no)
            payment.save()

class HackOrder(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = serializers.OrderSerializer

    def get(self, request, format=None):
        results = models.Order.objects.exclude(delivery_status__in=[40,60]).values('user').annotate(sum_orders=Sum('amount')).order_by("user")
        data = {}
        data['total']=0
        ret = []
        for result in results:
            if result['sum_orders']>80:
                ret.append(result)
                data['total'] = data['total']+1
        data['result']=ret
        return Response(data)





