# -*- encoding: utf8 -*-

import redis, ujson, hashlib, time, dateutil, json
import datetime as dt
import dateutil.parser
import requests
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

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
from notifications import notify
from rawpaginator.paginator import RawQuerySetPaginator
from paypalrestsdk import Payout, ResourceNotFound
from paypalrestsdk.openid_connect import Tokeninfo, Userinfo
import paypalrestsdk

from constance import config

from unify_django.permissions import IsOwnerOrReadOnly
from unify_django import utils
from unify_django import api_utils
from serializers import *
from models import *

from onedollar import tasks

from django.http import HttpResponse,JsonResponse
from django.db import connection
import random

r = get_redis_connection()

@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'users-signup': reverse('users-signup', request=request, format=format),
        'users-list': reverse('users-list', request=request, format=format),
        'users-profile': reverse('users-profile', request=request, format=format),
        'users-detail': reverse('users-detail', kwargs={'pk': request.user.id or 0}, request=request, format=format),
    })


class IsCreatorOrWinnerOrReadOnly(permissions.IsAuthenticated):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        if hasattr(obj, 'creator') and obj.creator == request.user:
            print '>>>>', 1, obj.creator, request.user
            return True
        elif hasattr(obj, 'winner') and obj.winner == request.user:
            keys = request.DATA.keys()
            return len(keys) == 1 and 'should_display_winner_popup' in keys
        return False


class UserView:
    queryset = OneDollarUser.objects.annotate(Count('product')) 
    # so luong product moi user co 
    serializer_class = UserSerializer
    permission_classes = (IsOwnerOrReadOnly,)


class UserList(UserView, generics.ListAPIView):
    pass


class UserDetail(UserView, generics.RetrieveUpdateAPIView):
    pass

class UserReferrer(UserView, generics.RetrieveAPIView):
    lookup_field = 'referral_code'


class UserProfile(UserView, generics.GenericAPIView):
    serializer_class = UserWithTokenSerializer

    def post(self, request, format=None):
        fb_token = request.DATA.get('fb_token')
        gp_token = request.DATA.get('gp_token')
        email = request.DATA.get('email')
        password = request.DATA.get('password')

        user = None

        if request.user.is_authenticated():
            user = request.user
        elif fb_token:
            user = OneDollarUser.objects.get_or_create_user_from_facebook(fb_token, should_create=False)
        elif gp_token:
            user = OneDollarUser.objects.get_or_create_user_from_googleplus(gp_token, should_create=False)
        elif email and password:
            user = authenticate(email=email, password=password)

        if not user:
            return Response({'user': 'INVALID_PROFILE'}, status=status.HTTP_400_BAD_REQUEST)

        if request.session.get('_auth_user_id', 0) != user.id:
            # create logged in session for the user if not available
            utils.login_user(request, user)

        if type(user) == OneDollarUser:
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        return Response({'user': 'INVALID_PROFILE'}, status=status.HTTP_400_BAD_REQUEST)

    def metadata(self, request):
        ret = super(UserProfile, self).metadata(request)

        ret['parameters'] = {'post': {
            "fb_token": {
                "type": "string",
                "description": "Facebook token. Optional. Only used when login is needed.",
                "required": False
            },
        }}

        return ret


class UserSignUp(generics.CreateAPIView):
    serializer_class = UserSignupSerializer

    def post(self, request, format=None):
        fb_token = request.DATA.get('fb_token')
        gp_token = request.DATA.get('gp_token')
        user = None

        try:
            if fb_token or gp_token:
                default_username = request.DATA.get('username')
                # TODO can be dangerous here?!? (send a FB token w/o email and force use any other email)
                default_email = request.DATA.get('email')

                if fb_token:
                    user = OneDollarUser.objects.get_or_create_user_from_facebook(fb_token, default_username, default_email)
                else:
                    user = OneDollarUser.objects.get_or_create_user_from_googleplus(gp_token)

                if not user:
                    raise api_utils.BadRequest('UNABLE_TO_LOGIN')
                else:
                    user.country_id = request.DATA.get('country')
                    user.deviceID = request.DATA.get('deviceID', None)
                    user.platform = request.DATA.get('platform', None)
                    if not user.referrer:
                        referrer = OneDollarUser.objects.filter(referral_code=request.DATA.get('referrer', None)).first()

                        if referrer:
                            user.referrer = referrer

                    user.save()
            else:
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.save(serializer)
                user = serializer.instance

            serializer = UserWithTokenSerializer(user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            raise ValidationError({'username': str(e[1])})

# For merchants
class MerchantsSignUp(generics.CreateAPIView):
    serializer_class = MerchantsSignupSerializer

    def post(self, request, format=None):
        user = None
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        user = serializer.instance
        serializer = UserWithTokenSerializer(user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CountryList(generics.ListAPIView):
    serializer_class = CountrySerializer
    queryset = Country.objects.filter(status=Country.STATUS_ENABLE)
    paginator = None


class CategoryList(generics.ListAPIView):
    serializer_class = CategorySerializer
    queryset = Category.showable.all()
    paginator = None

class CategoryListTest(generics.ListAPIView):
    serializer_class = CategoryTestSerializer
    queryset = CategoryTest.objects.all()
    paginator = None

class BrandList(generics.ListAPIView):
    serializer_class = BrandSerializer
    queryset = Brand.objects.all()
    paginator = None


class ProductListCreate(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    queryset = Product.showable.prefetch_related('photos', 'bets').order_by('-creation_date')
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        ret = super(ProductListCreate, self).get_queryset()
        ret = ret.filter(Q(end_date__gt=timezone.now()-dt.timedelta(days=config.HIDE_WON_PRODUCT)) | Q(end_date=None))
        # ret = ret.filter(Q(winner__isnull=True)|Q())
        ret = ret.exclude(creation_date__gte=timezone.now())

        if not self.request.user.is_staff:
            ret = ret.filter(country=self.request.user.country_id)

        is_sponsored = self.request.GET.get('is_sponsored', True)
        category = self.request.GET.get('category', None)
        if category:
            ret = ret.filter(category=category)
            is_sponsored = False

        ret = ret.filter(is_sponsored=is_sponsored)

        search_query = self.request.GET.get('search_query', None)
        if search_query:
            ret = ret.filter(title__icontains=search_query)

        order_by = self.request.GET.get('order_by', None)
        if order_by and (order_by.endswith('price') or order_by.endswith('sold_tickets')
                or order_by.endswith('creation_date') or order_by.endswith('finish')):
            if order_by == 'finish':
                ret = ret.annotate(finish=F('quantity')-F('sold_tickets')).order_by('finish')
            elif order_by.endswith('price'):
                value = F('quantity') * F('ticket_price')
                value.output_field = DecimalField()
                ret = ret.annotate(value=value)
                ret = ret.order_by('-value') if order_by[0] == '-' else ret.order_by('value')
            else:
                ret = ret.order_by(order_by)
        else:
            ret = ret.order_by('-creation_date')
        return ret


class ProductRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    queryset = Product.showable.all()
    permission_classes = (IsCreatorOrWinnerOrReadOnly,)
        
class ProductPhotoDelete(generics.DestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return ProductPhoto.objects.filter(product__creator=self.request.user)


class ProductShare(generics.GenericAPIView):
    queryset = Product.showable.all()
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        try:
            token = request.data.get('token', None)

            if not token:
                raise api_utils.BadRequest('TOKEN_INVALID')

            instance = self.get_object()
            instance.share_to_facebook(token)

            return Response({'result': True})
        except Exception as e:
            print '___', e
            return Response({'result': False}, status=status.HTTP_400_BAD_REQUEST)


# TODO should do bulk translate for optimization
def translate_user_ids(message):
    if type(message['user']) == int:
        user_id = message['user']
        message['user'] = LiteUserSerializer(OneDollarUser.objects.filter(pk=user_id).first()).data
    message['creation_date_text'] = calc_timesince(dateutil.parser.parse(message['creation_date']))
    return message


def get_lastread_key(channel_key, user_id):
    return '{}_lastread_{}'.format(channel_key, user_id)

class BaseCommentAPIView(generics.GenericAPIView):
    obj = None
    serializer_class = CommentSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = LimitOffsetPagination

    def get_lastread_key(self):
        self.obj = self.get_object()
        channel_key = self.get_redis_storage_channel()
        lastread_key = get_lastread_key(channel_key, self.request.user.id)

        return lastread_key

    def get_redis_storage_channel(self):
        return ''

    def get_redis_publish_channel(self, obj_id):
        return self.get_redis_storage_channel()

    def get(self, request, *args, **kwargs):
        self.obj = self.get_object()
        channel_key = self.get_redis_storage_channel()

        try:
            self.paginator.limit = self.paginator.get_limit(request)
            self.paginator.offset = self.paginator.get_offset(request)
            self.paginator.count = r.llen(channel_key)
            self.paginator.request = request

            found_last_message = False
            if request.GET.get('from') == 'bechat' and \
                    request.user and request.user.is_authenticated and \
                    request.user.is_staff:
                lastread = (dt.datetime.now()-dt.timedelta(days=60)).isoformat()
            else:
                lastread = r.get(self.get_lastread_key())
            messages = []

            while not found_last_message:
                end = -1 - self.paginator.offset
                start = end - self.paginator.limit + 1
                redis_messages = r.lrange(channel_key, start, end)
                last_message_date = None
                page_messages = []

                if not redis_messages:
                    break

                for msg_str in redis_messages:
                    message = ujson.loads(msg_str)
                    creation_date = dateutil.parser.parse(message['creation_date'])
                    message['creation_date_text'] = calc_timesince(creation_date)
                    message = translate_user_ids(message)
                    page_messages.append(message)

                    if not last_message_date:
                        last_message_date = message['creation_date']

                if last_message_date <= lastread:
                    found_last_message = True
                else:
                    self.paginator.offset += self.paginator.limit

                messages = page_messages + messages

            ret = self.paginator.get_paginated_response(messages)
            ret.data['lastread'] = r.get(self.get_lastread_key())
            return ret
        except Exception as e:
            print e
            return Response({'result': False, 'error': 'INVALID_DATA'})

    def handle_extra_data(self, data):
        return data

    def post(self, request, *args, **kwargs):
        self.obj = self.get_object()
        channel_key = self.get_redis_storage_channel()
        channel_publish_key = self.get_redis_publish_channel(self.obj.id)
        request.data['user'] = request.user.id
        request.data['creation_date'] = timezone.now()
        request.data['id'] = '{}_{}'.format(channel_key,
            hashlib.sha1('{}{}{}'.format(request.user.id,
            time.mktime(request.data['creation_date'].timetuple()),
            utils.generate_random_string())).hexdigest()[:15])
        self.handle_extra_data(request.data)

        serializer = self.get_serializer(request.data)
        data = serializer.data
        data['creation_date_text'] = calc_timesince(request.data['creation_date'])
        self.message = ujson.dumps(data)

        r.rpush(channel_key, self.message)

        self.message = ujson.dumps(translate_user_ids(data))
        if not channel_publish_key.startswith('notifications') or (channel_publish_key.startswith('notifications')
                and r.exists(channel_publish_key)):
            r.publish(channel_publish_key, self.message)
        else:
            tasks.send_pushnotifs([self.obj.push_channel], {
                'body': u'{} has just sent you a message'.format(request.user.get_full_name()),
                'product_id': self.product,
                'sender_id': request.user.id,
                'type': 'USER_COMMENT',
            })
        self.obj.append_notification(self.obj.chat_notification_key, self.product)

        return Response({'result': 'OK', 'error': None})


class ProductComments(BaseCommentAPIView):
    queryset = Product.showable.all()

    def get_redis_storage_channel(self):
        return 'comments.product.{}'.format(self.obj.id)

    def handle_extra_data(self, data):
        data['product'] = self.obj.id
        data['to_user'] = None


class ProductBetsPaginator(PageNumberPagination):
    max_page_size = 100

    def get_page_size(self, request):
        return 50

class ProductBets(generics.ListAPIView):
    queryset = Bet.objects.order_by('-creation_date')
    serializer_class = BetFullSerializer
    pagination_class = ProductBetsPaginator

    def get_queryset(self):
        try:
            product_id = self.kwargs.get('pk', None)

            if product_id:
                return super(ProductBets, self).get_queryset().filter(product=product_id)
            else:
                raise Exception()
        except Product.DoesNotExist:
            raise api_utils.BadRequest('INVALID_PRODUCT')

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            if self.request.version == '2' and self.pagination_class is not None:
                self._paginator = self.pagination_class()
            else:
                self._paginator = None
        return self._paginator

class Product10BetsLast(generics.ListAPIView):
    queryset = Bet.objects.order_by('-creation_date')[:10]
    serializer_class = BetFullSerializer
    # pagination_class = ProductBetsPaginator


def get_redis_chat_thread_key(user1, user2, product_id):
    user1, user2 = min(user1, user2), max(user1, user2)
    return 'comments.product.{}.user.{}_{}'.format(product_id, user1, user2)

class UserComments(BaseCommentAPIView):
    queryset = OneDollarUser.objects.all()

    def get_redis_storage_channel(self):
        if not self.product or not Product.objects.filter(pk=self.product).exists():
            raise api_utils.BadRequest('INVALID_PRODUCT')
        return get_redis_chat_thread_key(self.request.user.id, self.obj.id, self.product)

    def get_redis_publish_channel(self, obj_id):
        return 'notifications.user.{}'.format(obj_id)

    def get(self, request, *args, **kwargs):
        self.product = kwargs.get('product', None)
        return super(UserComments, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.product = request.data.get('product', None)
        ret = super(UserComments, self).post(request, *args, **kwargs)
        r.publish(self.get_redis_publish_channel(request.user.id), self.message)
        Product.objects.filter(pk=self.product).update(latest_chat_date=dt.datetime.now())
        return ret

    def handle_extra_data(self, data):
        data['to_user'] = self.obj.id


class ProductCommentsLastRead(ProductComments):
    def get(self, request, *args, **kwargs):
        self.product = kwargs.get('product', None)
        lastread_key = self.get_lastread_key()
        ret = r.get(lastread_key)
        return Response({'lastread': ret})

    def post(self, request, *args, **kwargs):
        self.product = kwargs.get('product', None)
        lastread = request.data.get('lastread', None)

        if not lastread:
            raise api_utils.BadRequest('INVALID_LASTREAD')

        lastread_key = self.get_lastread_key()
        r.set(lastread_key, lastread)
        return Response({'result': 'OK'})


class UserCommentsLastRead(ProductCommentsLastRead, UserComments):
    queryset = OneDollarUser.objects.all()

    def get_redis_storage_channel(self):
        return UserComments.get_redis_storage_channel(self)


class ForgetPassword(APIView):
    datetime_format = '%Y%m%d%H%M%S'

    def get_reset_code(self, email, expired_time=None):
        if not expired_time:
            expired_time = (dt.datetime.now() + relativedelta.relativedelta(hours=24)).strftime(self.datetime_format)

        code = '{}++{}++{}'.format(settings.SECRET_KEY, email, expired_time)
        return '{}_{}_{}'.format(hashlib.sha1(code).hexdigest(), expired_time, email)

    def post(self, request, format=None):
        reset_code = request.data.get('code', None)
        if not reset_code:
            email = self.request.data.get('email')

            if OneDollarUser.objects.filter(email=email).first():
                reset_link = settings.ONEDOLLAR_BIZ_URL + 'reset-password/?code={}'.format(self.get_reset_code(email))

                subject = 'OneDollar - Reset password requested'
                html_content = render_to_string('email/password_reset.html', {'reset_link':reset_link})

                tasks.send_email(subject, html_content, [email])
            else:
                raise api_utils.BadRequest('EMAIL_NOT_EXISTS')

            return Response({'message': 'An email was sent to your email. '
                                        'Please click on the link in it to verify your email address.'
                            , 'success': True})
        else:
            password = self.request.data.get('password')
            if not password:
                raise api_utils.BadRequest('NEW_PASSWORD_MISSING')

            code, expired_time, email = '', '', ''
            try:
                code, expired_time, email = reset_code.split('_', 2)

                if reset_code != self.get_reset_code(email, expired_time):
                    raise api_utils.BadRequest('INVALID_RESET_CODE')
            except:
                raise api_utils.BadRequest('INVALID_RESET_CODE')

            if dt.datetime.now().strftime(self.datetime_format) > expired_time:
                raise api_utils.BadRequest('RESET_CODE_EXPIRED')

            user = OneDollarUser.objects.filter(email=email).first()
            if not user:
                raise api_utils.BadRequest('INVALID_USER')

            user.set_password(password)
            user.save()

            return Response({'message': 'Password reset is successful.', 'success': True})

        return Response({
            'error': 'Error! Can\'t start forget password process',
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)


class SendVerificationEmail(APIView):
    def get_verification_code(self, user):
        code = '{}++{}++{}'.format(settings.SECRET_KEY, user.id, user.email)
        return '{}_{}'.format(user.id, hashlib.sha1(code).hexdigest())

    def post(self, request, format=None):
        verification_code = request.data.get('code', None)
        if not verification_code:
            if not (request.user and request.user.is_authenticated() and request.user.email):
                return Response({
                    'error': 'Error! Can\'t start email verification process',
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)

            verification_link = settings.ONEDOLLAR_BIZ_URL + 'merchants/account-validated/?code={}'.format(self.get_verification_code(request.user))

            subject = 'OneDollar - Validate your account first'
            html_content = render_to_string('email/validation.html', {'verification_link':verification_link})
            tasks.send_email(subject, html_content, [request.user.email])

            return Response({'message': 'An email was sent to your email. '
                                        'Please click on the link in it to verify your email address.'
                            , 'success': True})
        else:
            user_id, code = verification_code.split('_')
            user = OneDollarUser.objects.filter(pk=user_id).first()

            if not user:
                raise api_utils.BadRequest('INVALID_USER')

            if verification_code == self.get_verification_code(user):
                user.is_email_verified = True
                user.save()

                tasks.send_pushnotifs([user.push_channel], {
                    'body': u'Your account has just been updated',
                    'user_id': user.id,
                    'type': 'PROFILE_UPDATED',
                })

                return Response({'message': 'Email verification is successful.', 'success': True})
            else:
                raise api_utils.BadRequest('INVALID_EMAIL_VERIFICATION_CODE')

        # return Response({
        #     'error': 'Error! Can\'t start email verification process',
        #     'success': False
        # }, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
def CheckVerificationEmail(request):
    verification_code = request.POST.get('code', None)
    user_id, code = verification_code.split('_')
    user = OneDollarUser.objects.filter(pk=user_id).first()
    if not user:
        raise api_utils.BadRequest('INVALID_USER')
    code = '{}++{}++{}'.format(settings.SECRET_KEY, user.id, user.email)
    if verification_code == '{}_{}'.format(user.id, hashlib.sha1(code).hexdigest()):
        user.is_email_verified = True
        user.save()

        tasks.send_pushnotifs([user.push_channel], {
            'body': u'Your account has just been updated',
            'user_id': user.id,
            'type': 'PROFILE_UPDATED',
        })
        response = {
            'message' : 'Email verification is successful.',
            'success': True
        }
        return JsonResponse(response)
    else:
        raise api_utils.BadRequest('INVALID_EMAIL_VERIFICATION_CODE')


class BetView(generics.CreateAPIView):
    serializer_class = BetSerializer
    queryset = Bet.objects.all()

    def perform_create(self, serializer):
        cursor = connection.cursor()
        discount = 1
        if UserCatSpin.objects.filter(user=self.request.user):
            usercat = UserCatSpin.objects.get(user=self.request.user)
            discount =  1-usercat.discount 
        else: 
            usercat = UserCatSpin(user=self.request.user)
            usercat.save()
            usercat = UserCatSpin.objects.get(user=self.request.user)
            discount =  1-usercat.discount
        # print discount
        product = None
        try:
            product = Product.objects.get(pk=self.request.data.get('product'))
        except Exception as e:
            raise api_utils.BadRequest('INVALID_PRODUCT')

        if not self.request.user.is_authenticated():
            raise exceptions.AuthenticationFailed()

        if not self.request.user.is_verified:
            raise api_utils.BadRequest('ACCOUNT_NOT_VERIFIED_YET')

        if product.creator == self.request.user:
            raise api_utils.BadRequest('CANT_BET_OWN_PRODUCT')

        if product.end_date and product.end_date < timezone.now():
            raise api_utils.BadRequest('CANT_BET_EXPIRED_PRODUCT')

        if product.total_tickets and product.total_tickets <= product.sold_tickets:
            raise api_utils.BadRequest('NO_TICKET_LEFT')

        if not product.is_sponsored:
            if self.request.user.credits < float(product.ticket_price)*discount:
                if self.request.user.free_credits >= float(product.ticket_price)*discount:
                    raise api_utils.BadRequest('FREE_CREDITS_FOR_SPONSORED_PRODUCT_ONLY')
                raise api_utils.BadRequest('NOT_ENOUGH_CREDITS')
        elif self.request.user.total_credits < float(product.ticket_price)*discount:
            raise api_utils.BadRequest('NOT_ENOUGH_CREDITS')

        try:
            # print "test user"
            # print self.request.user
            bet = product.buy_ticket(self.request.user)

            if bet == None:
                raise api_utils.InternalServerError('NO_TICKET_LEFT')

            user = OneDollarUser.objects.filter(pk=self.request.user.id).first()
            # if user and user.email and user.total_credits == 0:
                # subject = u'OneDollar – Top-up your balance'
                # html_content = render_to_string('email/topup.html', {'name':user.first_name})

                # tasks.send_email(subject, html_content, [user.email])
            if usercat.slot_1==UserCatSpin.FREE:
                usercat.slot_1=UserCatSpin.FULL
            elif usercat.slot_2==UserCatSpin.FREE:
                usercat.slot_2=UserCatSpin.FULL
            elif usercat.slot_3==UserCatSpin.FREE:
                usercat.slot_3=UserCatSpin.FULL
            elif usercat.slot_4==UserCatSpin.FREE:
                usercat.slot_4=UserCatSpin.FULL
            usercat.save()

            notify.send(self.request.user, recipient=product.creator,
                    verb=_('put a bet on your product'), target=product)

            serializer.instance = bet
        except (api_utils.InternalServerError, api_utils.BadRequest) as e:
            raise e
        except Exception as e:
            raise exceptions.ValidationError(e.message)

class MyNotification(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return Notification.objects.filter(Q(recipient=self.request.user)|Q(verb='has won the product')).distinct()

class MyBetProductList(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = (permissions.IsAuthenticated,)
    chat_user_field = None

    def get_queryset(self):
        return Product.showable.prefetch_related('photos', 'bets')\
            .filter(bets__user=self.request.user).distinct()

    def get_serializer(self, *args, **kwargs):
        serializer = super(MyBetProductList, self).get_serializer(*args, **kwargs)

        if self.request.GET.get('chat', False) and self.chat_user_field:
            for data in serializer.data:
                data['latest_chat'] = None
                chat_thread_key = get_redis_chat_thread_key(self.request.user.id, data[self.chat_user_field]['id'], data['id'])
                latest_chat = r.lindex(chat_thread_key, -1)
                if latest_chat:
                    data['latest_chat'] = translate_user_ids(ujson.loads(latest_chat))
                    last_read = r.get(get_lastread_key(chat_thread_key, self.request.user.id))
                    data['latest_chat']['unread'] = last_read is None or data['latest_chat']['creation_date'] > last_read

        return serializer

class ProductListOtherUserPetOn(generics.ListAPIView):
    serializer_class = ProductOtherUserPetOnSerializer
    permission_classes = (permissions.IsAuthenticated,)
    chat_user_field = None

    def get_queryset(self):
        return Product.showable.prefetch_related('photos', 'bets')\
            .filter(bets__user=self.request.user).distinct()

    def get_serializer(self, *args, **kwargs):
        serializer = super(ProductListOtherUserPetOn, self).get_serializer(*args, **kwargs)

        if self.request.GET.get('chat', False) and self.chat_user_field:
            for data in serializer.data:
                data['latest_chat'] = None
                chat_thread_key = get_redis_chat_thread_key(self.request.user.id, data[self.chat_user_field]['id'], data['id'])
                latest_chat = r.lindex(chat_thread_key, -1)
                if latest_chat:
                    data['latest_chat'] = translate_user_ids(ujson.loads(latest_chat))
                    last_read = r.get(get_lastread_key(chat_thread_key, self.request.user.id))
                    data['latest_chat']['unread'] = last_read is None or data['latest_chat']['creation_date'] > last_read

        return serializer

class UserLuckyNumber(UserView,generics.ListAPIView):
    serializer_class = BetView
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        user = OneDollarUser.objects.get(pk=pk)
        user.second_chance_4h_48h=0
        user.save()
        userlucky = UserLucky.objects.filter(user=user)
        if userlucky:
            row=UserLucky.objects.get(user=user)
            row.count = row.count+1
            row.save()
            if userlucky.count<=2:
                ret=1
            else:
                prod = Product.objects.filter(Q(Q(sold_tickets__lt=F('quantity'), end_date=None) | Q(sold_tickets__lt=F('quantity'),end_date__gt=timezone.now()), winner=None,is_sponsored=1))
                if prod:
                    ret=random.randint(0,1)
                else:
                    ret=0
        else:
            new = UserLucky(user=user,count=1)
            new.save()
            ret=1
        data ={}
        data["result"]=ret
        if ret==1:
            gift=Product.objects.filter(Q(Q(sold_tickets__lt=F('quantity'), end_date=None) | Q(sold_tickets__lt=F('quantity'),end_date__gt=timezone.now()), winner=None,is_sponsored=1)).order_by('-creation_date')[0]
            if gift:
                bet = gift.buy_ticket(user,0)
                data["number"] = bet.number
                photo=ProductPhoto.objects.filter(product=gift)[0]
                data["photo"]=MEDIA_URL + str(photo.image)

        return Response(data)


class UserProductList(MyBetProductList):
    def get_queryset(self):
        creator = self.request.user

        try:
            pk = self.kwargs.get('pk', 'me')
            if pk != 'me':
                creator = OneDollarUser.objects.get(pk=pk)
        except OneDollarUser.DoesNotExist:
            raise api_utils.BadRequest('INVALID_USER')

        return Product.showable.prefetch_related('photos')\
            .filter(creator=creator).distinct().order_by('-creation_date')


class UserSellingProductList(UserProductList):
    def get_queryset(self):
        ret = super(UserSellingProductList, self).get_queryset()
        return ret.filter(Q(end_date__gt=timezone.now()) | Q(end_date=None),
                winner=None)


class UserSoldProductList(UserProductList):
    chat_user_field = 'winner'

    def get_queryset(self):
        ret = super(UserSoldProductList, self).get_queryset()
        order_col = '-latest_chat_date' if self.request.GET.get('chat', False) else '-end_date'
        return ret.filter(~Q(winner=None) & ~Q(win_number=None)).order_by(order_col)


class MyInProgressBetProductList(MyBetProductList):
    def get_queryset(self):
        return self.request.user.get_inprogress_bets()

    def paginate_queryset(self, raw_queryset):
        if self.paginator is None:
            return None

        page_number = self.request.query_params.get(self.paginator.page_query_param, 1)
        page_size = self.paginator.get_page_size(self.request)

        raw_queryset = RawQuerySetPaginator(raw_queryset, page_size)
        self.paginator.page = raw_queryset.page(page_number)
        self.paginator.request = self.request
        total = raw_queryset.count
        raw_queryset = list(raw_queryset.page(page_number))
        prefetch_related_objects(self.paginator.page, ['photos', 'bets'])

        return list(self.paginator.page)

    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.paginator.page.paginator.count),
            ('next', self.paginator.get_next_link()),
            ('previous', self.paginator.get_previous_link()),
            ('results', data)
        ]))


class MyWinBetProductList(MyBetProductList):
    chat_user_field = 'creator'

    def get_queryset(self):
        queryset = super(MyWinBetProductList, self).get_queryset()
        order_col = '-latest_chat_date' if self.request.GET.get('chat', False) else '-end_date'
        return queryset.filter(Q(winner=self.request.user)).order_by(order_col)


class MyFailedBetProductList(MyBetProductList):
    def get_queryset(self):
        queryset = super(MyFailedBetProductList, self).get_queryset()
        return queryset.filter(~Q(winner=self.request.user) & ~Q(winner=None)).order_by('-end_date')

class UserRatingList(generics.ListAPIView):
    serializer_class = RatingListSerializer

    def get_queryset(self):
        rating_to = self.request.user

        try:
            pk = self.kwargs.get('pk', 'me')
            if pk != 'me':
                rating_to = OneDollarUser.objects.get(pk=pk)
        except OneDollarUser.DoesNotExist:
            raise api_utils.BadRequest('INVALID_USER')

        return OneDollarUserRating.objects.prefetch_related('rating_from')\
            .filter(rating_to=rating_to).order_by('-creation_date').distinct()


class RatingView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = RatingSerializer

    def get_serializer(self, *args, **kwargs):
        kwargs['data']['creation_date'] = timezone.now()
        kwargs['data']['rating_from'] = int(self.request.user.id)
        return super(RatingView, self).get_serializer(*args, **kwargs)


class TransactionTopup(generics.ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = (permissions.IsAuthenticated,)
    paginator = None

    def get_queryset(self):
        return Transaction.get_topups_in_90_days().filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        transaction_type = request.data.get('transaction_type', None)
        if not self.request.user.is_verified and transaction_type < Transaction.TYPE_REWARD:
            raise api_utils.BadRequest('ACCOUNT_NOT_VERIFIED_YET')

        return super(TransactionTopup, self).post(request, *args, **kwargs)


class UserReportingTypeList(generics.ListAPIView):
    serializer_class = UserReportingTypeSerializer
    queryset = UserReportingType.objects.filter(status=UserReportingType.STATUS_ENABLE)
    paginator = None


class ProductReportingTypeList(generics.ListAPIView):
    serializer_class = ProductReportingTypeSerializer
    queryset = ProductReportingType.objects.filter(status=ProductReportingType.STATUS_ENABLE)
    paginator = None


class ReportUserCreate(generics.CreateAPIView):
    serializer_class = UserReportingSerializer
    queryset = OneDollarUser.reportings.through
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def post(self, request, *args, **kwargs):
        user = request.data.get('user', None)
        user_report = self.queryset.objects.filter(user=user, creator=request.user).first()

        if user_report:
            user_report.report_type_id = request.data.get('report_type', None)
            user_report.save()

            serializer = self.get_serializer()
            serializer.instance = user_report
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return self.create(request, *args, **kwargs)


class ReportProductCreate(generics.CreateAPIView):
    serializer_class = ProductReportingSerializer
    queryset = Product.reportings.through
    permission_classes = (permissions.IsAuthenticated,)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def post(self, request, *args, **kwargs):
        product = request.data.get('product', None)
        product_report = self.queryset.objects.filter(product=product, creator=request.user).first()

        if product_report:
            product_report.report_type_id = request.data.get('report_type', None)
            product_report.save()

            serializer = self.get_serializer()
            serializer.instance = product_report
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return self.create(request, *args, **kwargs)


class Claim(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        amounts = request.user.claim_amounts
        return Response(amounts)

    def post(self, request, format=None):
        authorization_code = request.data.get('authorization_code', None)
        email = None

        if not authorization_code:
            raise api_utils.BadRequest('INVALID_AUTHORIZATION_CODE')

        paypalrestsdk.configure({
            "mode":settings.PAYPAL_MODE,
            "client_id":settings.PAYPAL_CLIENT_ID,
            "client_secret":settings.PAYPAL_CLIENT_SECRET
        })

        try:
            tokeninfo = Tokeninfo.create(authorization_code)
            userinfo = tokeninfo.userinfo()
            print userinfo
            email = userinfo.email
        except Exception as e:
            print e
            raise api_utils.BadRequest('INVALID_AUTHORIZATION_CODE')

        if not email:
            raise api_utils.BadRequest('EMAIL_NOT_RETRIEVABLE')

        price = 0
        product_ids = []

        for product in request.user.claim_products:
            price += product.sold_tickets*product.ticket_price
            product_ids.append(str(product.id))

        if price > 0:
            price = int(price * settings.PERCENT_CLAIM_PAYOUT * 100)/100.0
            payout = Payout({
                "sender_batch_header": {
                    "sender_batch_id": "batch_"+hashlib.sha1('_'.join(product_ids)).hexdigest()[:10],
                    "email_subject": "You have a payment"
                },
                "items": [
                    {
                        "recipient_type": "EMAIL",
                        "amount": {
                            "value": price,
                            "currency": "SGD"
                        },
                        "receiver": email,
                        "note": "Payment for {} claim products".format(len(product_ids)),
                    }
                ]
            })
            print payout
            if payout.create(sync_mode=True):
                Product.objects.filter(pk__in=product_ids).update(payout_date=timezone.now())

                print("payout [%s] created successfully" %
                    (payout.batch_header.payout_batch_id))
                return Response({'result': 'OK', 'error': None})
            else:
                print(payout.error)
                return Response({'result': 'NOK', 'error': payout.error})

        return Response({'result': 'OK', 'error': None})

class MyBadges(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        activity_badge = chat_badge = notification_badge = 0
        try:
            activity_badge = r.scard(request.user.activity_notification_key)
            chat_badge = r.scard(request.user.chat_notification_key)
            notification_badge = request.user.notifications.filter(unread=True).count()
        except:
            pass

        return Response({
            'activity': activity_badge,
            'chat': chat_badge,
            'common': notification_badge,
        })

    def delete(self, request, format=None):
        badge_type = request.DATA.get('badge_type', None)
        ids = request.DATA.get('ids', None)

        if not badge_type or not badge_type in ['activity', 'chat', 'common']:
            raise api_utils.BadRequest('INVALID_BADGE_TYPE')
        notification_key = getattr(request.user, '{}_notification_key'.format(badge_type), False)

        if not notification_key:
            raise api_utils.BadRequest('INVALID_NOTIFICATION_KEY')

        if ids != 'all':
            try:
                if not ids:
                    raise api_utils.BadRequest('INVALID_IDS')
                ids = [int(i) for i in ids.split(',')]
            except:
                raise api_utils.BadRequest('INVALID_IDS')

        if badge_type == 'common':
            qs = request.user.notifications.filter(unread=True)
            if ids != 'all':
                qs = qs.filter(id__in=ids)
            ret = qs.count()

            if ret > 0:
                qs.update(unread=False)
        elif badge_type == 'chat' or badge_type == 'activity':
            ret = r.srem(notification_key, *ids)

        return Response({'result': 'OK', 'items_read': ret})


class MyChatBadges(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        ret = r.smembers(request.user.chat_notification_key)
        if request.GET.get('from') == 'bechat' and \
                request.user and request.user.is_authenticated and \
                request.user.is_staff:
            for user in OneDollarUser.objects.exclude(pk=request.user.id).filter(is_staff=True):
                ret = ret.union(r.smembers(user.chat_notification_key))

        return Response(ret)

class BackendStats(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        if not request.user.is_staff:
            raise api_utils.BadRequest('REQUIRE_IS_STAFF')

        ret = {}

        try:
            ret['sum_topups'] = Transaction.get_sum_all_topups()
            ret.update(OneDollarUser.get_creation_stats())
            ret.update(OneDollarUser.get_user_flagged_stats())

            ret['chat'] = 0
            for creator in OneDollarUser.objects.filter(is_staff=True):
                ret['chat'] += r.scard(creator.chat_notification_key)
        except:
            pass

        return Response(ret)


class Settings(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        referral_url = request.build_absolute_uri(request.user.get_short_referral_link())
        ret = {
            'referral_sms': config.REFERRAL_SMS.replace('###url###', referral_url),
            'free_credits': config.THE_FREE_CREDITS_GIVEN,
            'quote1': config.QUOTE_1,
            'quote2': config.QUOTE_2,
            'quote3': config.QUOTE_3,
            'quote4': config.QUOTE_4,
            'quote5': config.QUOTE_5,
            'quote6': config.QUOTE_6,
            'quote7': config.QUOTE_7,
            'quote8': config.QUOTE_8,
            'quote9': config.QUOTE_9,
            'quote10': config.QUOTE_10,
            'hide_won_product': config.HIDE_WON_PRODUCT,
            'stripe_error_msg_insufficient_fund': config.STRIPE_ERROR_MSG_INSUFFICIENT_FUND,
            'stripe_error_msg_declined': config.STRIPE_ERROR_MSG_DECLINED,
            'stripe_error_msg_incorrect': config.STRIPE_ERROR_MSG_INCORRECT,
            'stripe_error_msg_notsupport': config.STRIPE_ERROR_MSG_NOTSUPPORT,
            'stripe_error_msg_risky': config.STRIPE_ERROR_MSG_RISKY,
            'five_stars_rating': config.FIVE_STARS_RATING,
            'give_5_get_5': config.GIVE_5_GET_5,
            'share_your_idea': config.SHARE_YOUR_IDEA,
            'referral_topup_require': config.REFERRAL_TOPUP_REQUIRE,
            'referral_topup_reward': config.REFERRAL_TOPUP_REWARD,
            'limit_amount_of_payment_per_week': config.LIMIT_AMOUT_OF_PAYMENT_PER_WEEK,
            'limit_number_of_payment_per_day': config.LIMIT_NUMBER_OF_PAYMENT_PER_DAY,
            'reward_value': config.REWARD_VALUE,
            'text_helptext_shop_intro': config.TEXT_HELPTEXT_SHOP_INTRO,
            'text_helptext_bet_intro': config.TEXT_HELPTEXT_BET_INTRO,
            'text_helptext_order_history_intro': config.TEXT_HELPTEXT_ORDER_HISTORY_INTRO,
            'text_header_cart': config.TEXT_HEADER_CART,
            'text_header_shop': config.TEXT_HEADER_SHOP,
            'text_header_bet': config.TEXT_HEADER_BET,            
            'text_cart_missed': config.TEXT_CART_MISSED,
            'text_cart_won': config.TEXT_CART_WON,
            'text_cart_bet': config.TEXT_CART_BET,
            'text_share': config.TEXT_SHARE,
            'text_share_description': config.TEXT_SHARE_DESCRIPTION,
            'text_share_url': config.TEXT_SHARE_URL,
            'text_draw_description': config.TEXT_DRAW_DESCRIPTION,
            'text_game_title': config.TEXT_GAME_TITLE,
            'text_game_helptext_title': config.TEXT_GAME_HELPTEXT_TITLE,
            'text_game_helptext_text': config.TEXT_GAME_HELPTEXT_TEXT,
            'require_coins_1': config.REQUIRE_COINS_1,
            'require_coins_2': config.REQUIRE_COINS_2,
            'require_coins_3': config.REQUIRE_COINS_3,
            'require_coins_4': config.REQUIRE_COINS_4,
            'require_coins_5': config.REQUIRE_COINS_5,
            'require_coins_6': config.REQUIRE_COINS_6,
            'require_coins_7': config.REQUIRE_COINS_7,
            'require_coins_8': config.REQUIRE_COINS_8,
            'discount_1': config.DISCOUNT_1,
            'discount_2': config.DISCOUNT_2,
            'discount_3': config.DISCOUNT_3,
            'discount_4': config.DISCOUNT_4,
            'discount_5': config.DISCOUNT_5,
            'discount_6': config.DISCOUNT_6,
            'discount_7': config.DISCOUNT_7,
            'discount_8': config.DISCOUNT_8,
            'discount_time_1': config.DISCOUNT_TIME_1,
            'discount_time_2': config.DISCOUNT_TIME_2,
            'discount_time_3': config.DISCOUNT_TIME_3,
            'discount_time_4': config.DISCOUNT_TIME_4,
            'discount_time_5': config.DISCOUNT_TIME_5,
            'discount_time_6': config.DISCOUNT_TIME_6,
            'discount_time_7': config.DISCOUNT_TIME_7,
            'discount_time_8': config.DISCOUNT_TIME_8,
            'daily_win_min': config.DAILY_WIN_MIN,
            'daily_win_max': config.DAILY_WIN_MAX,
            'claim_win_min': config.CLAIM_WIN_MIN,
            'claim_win_max': config.CLAIM_WIN_MAX,
            'install_apps_title': config.INSTALL_APPS_TITLE,
            'install_apps_description': config.INSTALL_APPS_DESCRIPTION,
            'install_apps_reward': config.INSTALL_APPS_REWARD,
            'text_warning_fraud': config.TEXT_WARNING_FRAUD,
            'text_find_out_more': config.TEXT_FIND_OUT_MORE,
        }

        return Response(ret)


class UserPushToken(APIView):
    def post(self, request, format=None):
        method = request.data.get('method', 'register')
        token = request.data.get('pushtoken', None)

        if not method or (method != 'register' and method != 'unregister'):
            raise api_utils.BadRequest('INVALID_METHOD')

        if not token:
            raise api_utils.BadRequest('INVALID_PUSHTOKEN')

        if method == 'register':
            if request.user and not request.user.is_authenticated():
                raise api_utils.BadRequest('INVALID_USER')

            token, created = OneDollarUserToken.objects.get_or_create(token=token)
            if token.user != request.user:
                token.user = request.user
                token.save()
        elif method == 'unregister':
            OneDollarUserToken.objects.filter(token=token).delete()

        return Response({'result': 'OK', 'error': None})


class TopupPackageList(generics.ListAPIView):
    serializer_class = TopupPackageSerializer
    queryset = TopupPackage.objects.all()
    paginator = None

# other-users-bet-on
class ProductsOtherUserBetOn(ProductListOtherUserPetOn):
    user_id=[]
    def get_queryset(self):
        try:
            product_id = self.kwargs.get('pk', None)
            self.product_id = product_id

            if product_id:
                userBetOns = Bet.objects.filter(product=product_id).values('user').distinct()
                for userBetOn in userBetOns:
                    # print "====Other user bet===="
                    # print userBetOn['user']
                    self.user_id.append(userBetOn['user'])
                # print self.get_inprogress_bets()
                return self.get_inprogress_bets()
            else:
                raise Exception()
        except Product.DoesNotExist:
            raise api_utils.BadRequest('INVALID_PRODUCT')

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            if self.request.version == '2' and self.pagination_class is not None:
                self._paginator = self.pagination_class()
            else:
                self._paginator = None
        return self._paginator

    def get_inprogress_bets(self):
        addQuery = ""
        if (len(self.user_id) < 1):
            pass
        # Have user_id
        addQuery = str(self.user_id[0])
        if (len(self.user_id) > 1):
            for user_id in self.user_id:
                if (self.user_id[0] != user_id):
                    addQuery += " || `onedollar_bet`.`user_id` = " + str(user_id)

        # print addQuery
        # print self.product_id
        return Product.objects.raw('''
                select *
                from `onedollar_product` p
                join (
                    select product_id, max(id) mid
                    from `onedollar_bet`
                    where `onedollar_bet`.`user_id` = %s
                    group by product_id
                    order by mid desc) b on p.id = b.`product_id`
                where end_date > '{}' or end_date IS NULL and product_id != %s ORDER BY `p`.`sold_tickets` DESC
            '''.format(timezone.now().strftime('%Y-%m-%d %H:%M:%S'))
            , [addQuery,self.product_id])

class CatShowHide(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        userlucky = UserLucky.objects.filter(user=request.user.id)
        query = Product.showable.prefetch_related('photos', 'bets').filter(bets__user=self.request.user).distinct()
        countMiss = query.filter(~Q(winner=self.request.user) & ~Q(winner=None)).order_by('-end_date').count()
        ret = {}
        ret['count_miss']=countMiss
        ret['status']=0
        if userlucky:
            ret['count_use']=UserLucky.objects.get(user=request.user).count
        else:
            ret['count_use']=0
            x = UserLucky(user=request.user)
            x.count = 0
            x.save()
        if ret['count_miss']>ret['count_use']:
            ret['status']=1
        y = UserLucky.objects.get(user=request.user.id)
        y.is_have_chance = ret['status']
        y.save()
        return Response(ret)

class CatSpin(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = CatSpinSerializer

    def get_queryset(self):
        user = OneDollarUser.objects.get(pk=self.request.user.id)
        if not(UserCatSpin.objects.filter(user=self.request.user.id)):
            x=UserCatSpin(user=user)
            x.save()
        
        userspin=UserCatSpin.objects.get(user=user)
        userspin.level=0
        i=1
        total=config.REQUIRE_COINS_1
        while total<userspin.coins:
            userspin.level=i
            i=i+1
            if i==1:
                temp=config.REQUIRE_COINS_1
            if i==2:
                temp=config.REQUIRE_COINS_2
            if i==3:
                temp=config.REQUIRE_COINS_3
            if i==4:
                temp=config.REQUIRE_COINS_4
            if i==5:
                temp=config.REQUIRE_COINS_5
            if i==6:
                temp=config.REQUIRE_COINS_6
            if i==7:
                temp=config.REQUIRE_COINS_7
            if i==8:
                temp=config.REQUIRE_COINS_8
            if i<9:
                total=total+temp
            else:
                break
        userspin.save()
        return UserCatSpin.objects.filter(user=user)
        
class CatSpinUncage(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self,request,pk):
        user = OneDollarUser.objects.get(pk=self.request.user.id)
        userspin=UserCatSpin.objects.get(user=user)
        print pk
        ret = {}
        if pk=='1':
            ret['daily_1']=dt.datetime.now()+dt.timedelta(minutes=config.TIME_DAILY)
            userspin.daily_1 = ret['daily_1']
        if pk=='2':
            userspin.daily_2=dt.datetime.now()+dt.timedelta(minutes=config.TIME_DAILY)
            ret['daily_2']=userspin.daily_2
        if pk=='10':
            userspin.time_1=dt.datetime.now()+dt.timedelta(minutes=config.TIME_UNCAGE)
            ret['time_1']=userspin.time_1
            userspin.slot_1=UserCatSpin.RUNNING
        if pk=='20':
            userspin.time_2=dt.datetime.now()+dt.timedelta(minutes=config.TIME_UNCAGE)
            ret['time_2']=userspin.time_2
            userspin.slot_2=UserCatSpin.RUNNING
        if pk=='30':
            userspin.time_3=dt.datetime.now()+dt.timedelta(minutes=config.TIME_UNCAGE)
            ret['time_3']=userspin.time_3
            userspin.slot_3=UserCatSpin.RUNNING
        if pk=='40':
            userspin.time_4=dt.datetime.now()+dt.timedelta(minutes=config.TIME_UNCAGE)
            ret['time_4']=userspin.time_4
            userspin.slot_4=UserCatSpin.RUNNING
        userspin.save()
        return Response(ret)

class GetCoins(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        user = OneDollarUser.objects.get(pk=self.request.user.id)
        userspin=UserCatSpin.objects.get(user=user)
        print pk
        temp = 0 
        ret = {}
        if pk=='1':
            userspin.daily_1=dt.datetime.now()+dt.timedelta(minutes=config.TIME_DAILY)
        if pk=='2':
            userspin.daily_2=dt.datetime.now()+dt.timedelta(minutes=config.TIME_DAILY)
        if pk=='10':
            userspin.time_1=dt.datetime.now()+dt.timedelta(minutes=config.TIME_UNCAGE)
            userspin.slot_1=UserCatSpin.FREE
            temp=1
        if pk=='20':
            userspin.time_2=dt.datetime.now()+dt.timedelta(minutes=config.TIME_UNCAGE)
            userspin.slot_2=UserCatSpin.FREE
            temp=1
        if pk=='30':
            userspin.time_3=dt.datetime.now()+dt.timedelta(minutes=config.TIME_UNCAGE)
            userspin.slot_3=UserCatSpin.FREE
            temp=1
        if pk=='40':
            userspin.time_4=dt.datetime.now()+dt.timedelta(minutes=config.TIME_UNCAGE)
            userspin.slot_4=UserCatSpin.FREE
            temp=1
        if not temp:
            prize = random.randint(config.DAILY_WIN_MIN,config.DAILY_WIN_MAX)
        else:
            prize = random.randint(config.CLAIM_WIN_MIN,config.CLAIM_WIN_MAX)
        userspin.coins = userspin.coins+prize
        userspin.save()
        ret = {}
        ret['prize']=prize
        return Response(ret)

class CatClaim(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        user = self.request.user
        userspin = UserCatSpin.objects.get(user=user)
        ret = {}
        i=userspin.level
        discount=0
        discountTime=0
        if i==1:
            discount=config.DISCOUNT_1
            discountTime=config.DISCOUNT_TIME_1
        if i==2:
            discount=config.DISCOUNT_2
            discountTime=config.DISCOUNT_TIME_2
        if i==3:
            discount=config.DISCOUNT_3
            discountTime=config.DISCOUNT_TIME_3
        if i==4:
            discount=config.DISCOUNT_4
            discountTime=config.DISCOUNT_TIME_4
        if i==5:
            discount=config.DISCOUNT_5
            discountTime=config.DISCOUNT_TIME_5
        if i==6:
            discount=config.DISCOUNT_6
            discountTime=config.DISCOUNT_TIME_6
        if i==7:
            discount=config.DISCOUNT_7
            discountTime=config.DISCOUNT_TIME_7
        if i==8:
            discount=config.DISCOUNT_8
            discountTime=config.DISCOUNT_TIME_8
        ret['discount']=discount/float(100)
        ret['discountTime']=discountTime
        while i>0:
            if i==1:
                temp=config.REQUIRE_COINS_1
            if i==2:
                temp=config.REQUIRE_COINS_2
            if i==3:
                temp=config.REQUIRE_COINS_3
            if i==4:
                temp=config.REQUIRE_COINS_4
            if i==5:
                temp=config.REQUIRE_COINS_5
            if i==6:
                temp=config.REQUIRE_COINS_6
            if i==7:
                temp=config.REQUIRE_COINS_7
            if i==8:
                temp=config.REQUIRE_COINS_8
            userspin.coins = userspin.coins-temp
            i=i-1
        userspin.level=0
        userspin.discount=discount/float(100)
        userspin.save()
        return Response(ret)

class StopDiscount(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def get(self, request, format=None):
        user = OneDollarUser.objects.get(pk=self.request.user.id)
        userspin = UserCatSpin.objects.get(user=user)
        userspin.discount=0
        userspin.save()
        return Response({"status":"success"})

class GetNoti(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = NotiSerializer

    def get_queryset(self):
        user = OneDollarUser.objects.get(pk=self.request.user.id)
        return WinnerProduct.objects.filter(Q(win1=user.id)|Q(win2=user.id)|Q(win3=user.id))

class GetDollarForProduct(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk, prize):
        user_id = request.user.id
        user = OneDollarUser.objects.get(pk=user_id)
        product_prize = Product.objects.get(pk=pk)
        product = WinnerProduct.objects.get(product=pk)

        ret = {}
        money=0
        ret['status']='fail'
        if int(prize)==1 and not product.win1==-1:
            product.win1=-1
            ret['status']='succsess'
        if int(prize)==2 and not product.win2==-1:
            money=product_prize.win_second_award
            product.win2=-1
            trans = Transaction(user=user,transaction_type=Transaction.TYPE_REWARD,amount=money)
            trans.save()
            user.collect_your_cash_4h_24h=0
            ret['status']='succsess'
        if int(prize)==3 and not product.win3==-1:
            money=product_prize.win_third_award
            product.win3=-1
            trans = Transaction(user=user,transaction_type=Transaction.TYPE_REWARD,amount=money)
            trans.save()
            user.collect_your_cash_4h_24h=0
            ret['status']='succsess'
        product.save()
        if product.win1==-1 and product.win2==-1 and product.win3==-1:
            product.delete()
        user.credits = user.credits+float(money)
        user.save()
        return Response(ret)


        


        