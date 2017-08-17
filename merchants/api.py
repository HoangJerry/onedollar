# -*- encoding: utf8 -*-

import redis, ujson, hashlib, time, dateutil, json
import datetime as dt
import dateutil.parser
import requests

from dateutil import relativedelta
from django.http import HttpResponseRedirect
from django.db.utils import IntegrityError
from django.contrib.auth import authenticate
from django.db import connection
from django.db.models import Q, F, Count, Expression
from django.db.models.fields import DecimalField
from django.db.models.query import prefetch_related_objects
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string

from django.utils.translation import ugettext_lazy as _
from rest_framework import generics, status, exceptions, permissions
from rest_framework.compat import OrderedDict
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework import permissions
from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination
from django_countries import countries
from rawpaginator.paginator import RawQuerySetPaginator

from constance import config

from unify_django.permissions import IsOwnerOrReadOnly
from unify_django import utils
from unify_django import api_utils

from serializers import *
from models import *
from onedollar import models as onedollar_models

from django.http import HttpResponse,JsonResponse
from django.db import connection
import random

import md5
from onedollar import tasks

@api_view(('GET',))
def api_root(request, format=None):
    return Response({
    })

class StoreView:
    permission_classes = (IsOwnerOrReadOnly,)
    queryset = Store.objects
    serializer_class = StoreSerializer

class StoreDetail(StoreView,generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        return Store.objects.filter(user=user)

    def post(self,request,format=None):
        if request.method == "POST" and (request.user and request.user.is_authenticated()):
            user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
            user.is_staff = True
            user.save()
            if not Store.objects.filter(user=user):
                x = Store(user=user)
                x.save()
                x = EmailFags(user=user)
                x.save()
            merchant = Store.objects.get(user = user)
            if request.DATA.get('email_payment'):
                merchant.email_payment =request.DATA.get('email_payment')
                merchant.provider_payment =request.DATA.get('provider_payment')
            else:
                merchant.store_platform =request.DATA.get('store_platform')
                merchant.url_store_platform =request.DATA.get('url_store_platform')
                merchant.revenue_last_year =request.DATA.get('revenue_lastyear')
                merchant.warehouse_located =request.DATA.get('warehouse_located')
                merchant.warehouse_street =request.DATA.get('warehouse_street')
                merchant.product_categories =request.DATA.get('product_categories')
                # merchant.provider_payment =request.DATA.get('provider_payment')
            if merchant.email_payment:
                user.is_payment_verified = True
                user.save()
            merchant.save()
        else:
            return super(StoreDetail, self).get_queryset()
        
        return Response(1)

class PhoneSendSms(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self,request,format=None):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        phone= request.DATA.get('phone')
        code = str(user.id)+str(phone) +'truong&hoang'
        
        mess = r"Your%20verification%20code%20for%20OneDollar%20is:%20"
        code = str(mess) + str(hashlib.sha1(code).hexdigest().upper()[-8:])

        ret ={}
        ret['status']=0
        if user.sms_count<=2:
            if tasks.send_sms(phone,code):
                user.sms_count=F('sms_count')+1
                ret['status']=1
            user.save()
        return Response(ret)

class PhoneVerify(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    # serializer_class = PhoneVerifySerializer

    def post(self,request,format=None):
        phone= request.DATA.get('phone')
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        code = str(user.id)+str(phone) +'truong&hoang'
        code = str(hashlib.sha1(code).hexdigest().upper()[-8:])

        code_from_user =request.DATA.get('code')
        ret ={}
        ret['status']=0
        if code==code_from_user:
            user.is_phone_verified=True
            user.phone=phone
            ret['status']=1
        user.save()
        return Response(ret)

class Term(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def get(self,request,format=None):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        user.is_accept_terms_of_service = True
        user.save()
        return Response('1')


class EmailStatus(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EmailFagsSerializer

    def get_queryset(self):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        if not EmailFags.objects.filter(user=user):
            x=EmailFags(user=user)
            x.save()
        return EmailFags.objects.filter(user=user)
    
    def post(self,request,format=None):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        if request.method == "POST":
            email_flag = EmailFags.objects.get(user = user)
            email_flag.receive_an_order =int(request.data.get('receive_an_order'))
            email_flag.approve_a_new_product =int(request.data.get('approve_a_new_product'))
            email_flag.received_a_payment_product =int(request.data.get('received_a_payment_product'))
            email_flag.do_not_send_me_any_of_these_emails =int(request.data.get('do_not_send_me_any_of_these_emails'))
            email_flag.save()
            return Response({'status':1})
        else:
            return super(EmailStatus, self).get_queryset()

class ChangeUserName(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self,request,format=None):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        current_pass = request.data.get('password')
        current_user = request.data.get('username')
        ret = {}
        ret['status'] = 0 
        if user.check_password(current_pass):
            try:
                user.username = current_user
                user.save()
                ret['status'] = 1
            except Exception as e:
                ret['error']= "STORE_NAME_EXITS"               
        return Response(ret)

class ChangeEmail(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self,request,format=None):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        current_pass = request.data.get('password')
        current_email = request.data.get('email')
        ret = {}
        ret['status'] = 0 
        if user.check_password(current_pass):
            try:
                user.email = current_email
                user.save()
                ret['status'] = 1
            except Exception as e:
                ret['error']= "EMAIL_EXITS"  
        else:
            ret['error']="PASSWORD_NOT_MATH"            
        return Response(ret)

class ChangePassword(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    
    def post(self,request,format=None):
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)

        current_pass = request.data.get('old-password')
        new_password = request.data.get('new-password')
        ret = {}
        ret['status'] = 0 
        ret['error']= "CURRENT_PASS_WRONG"               
        if user.check_password(current_pass):
            user.set_password(new_password)
            user.save()  
            ret['status'] = 1   
            ret['error']= ''              
        return Response(ret)

class SendOpenStoreEmail(APIView):

    def get(self, request, format=None):
        if not (request.user and request.user.is_authenticated() and request.user.email):
            return Response({
                'error': 'Error! Can\'t start email open store process',
                'status':0
            }, status=status.HTTP_400_BAD_REQUEST)
        store = Store.objects.get(user=request.user)
        store.status = Store.CONST_STATUS_PENDING
        store.save()
        verification_link = settings.ONEDOLLAR_BIZ_URL + 'admin/merchants/store/{}/'.format(store.id)
        # to_admin = onedollar_models.OneDollarUser.objects.filter(is_superuser=True)[0]
        subject = 'OneDollar - User request open store'
        html_content = render_to_string('email/openstore.html', {'verification_link':verification_link})
        tasks.send_email(subject, html_content, ['gpanot@giinger.com'])
        # tasks.send_email(subject, html_content, ['nhattruong0210@hotmail.com'])
        return Response({'status':1})

class SendRequestOrderEmail(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, format=None):
        if not (request.user and request.user.is_authenticated() and request.user.email):
            return Response({
                'error': 'Error! Can\'t start email request order process',
                'status':0
            }, status=status.HTTP_400_BAD_REQUEST)
        user = onedollar_models.OneDollarUser.objects.get(pk=self.request.user.id)
        creator = request.data.get('creator')
        usercreator = onedollar_models.OneDollarUser.objects.get(pk=creator)
        emailfag = EmailFags.objects.filter(user=usercreator)[0]
        if (emailfag.do_not_send_me_any_of_these_emails) or (not emailfag.receive_an_order):
            return Response({'status':1,'message':'False'})

        transaction_id = request.data.get('transaction_id')
        product_title = request.data.get('product_title')
        sku = request.data.get('sku')

        link = settings.ONEDOLLAR_BIZ_URL + "/merchants/"

        subject = 'You have a new order waiting for shipment'
        html_content = render_to_string('email/receiveneworder.html', {'email':user.email,
            'transaction_id':transaction_id,'product_title':product_title,'sku':sku,'link':link,})
        tasks.send_email(subject, html_content, [usercreator.email])
        # tasks.send_email(subject, html_content, ['ngochoang09121996@gmail.com'])
        return Response({'status':1})

def SendProductAprrovedEmail(product,creator):
    usercreator = onedollar_models.OneDollarUser.objects.get(pk=creator)
    emailfag = EmailFags.objects.filter(user=usercreator)[0]
    if (emailfag.do_not_send_me_any_of_these_emails) or (not emailfag.approve_a_new_product):
        return Response({'status':1,'message':'False'})
    subject = 'OneDollar - Approved your product'
    html_content = render_to_string('email/approve_a_new_product.html', {'product':product})
    tasks.send_email(subject, html_content, [usercreator.email])
    return Response({'status':1})

def SendPaymentHistoryEmail(user,day):
    emailfag = EmailFags.objects.filter(user=user)[0]
    if (emailfag.do_not_send_me_any_of_these_emails) or (not emailfag.received_a_payment_product):
        return Response({'status':1,'message':'False'})
    subject = 'OneDollar - Payment {}'.format(day)
    html_content = render_to_string('email/received_a_payment_product.html', {'day':day})
    tasks.send_email(subject, html_content, [user.email])
    return Response({'status':1})
