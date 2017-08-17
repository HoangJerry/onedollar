from rest_framework import fields, serializers
from rest_framework.reverse import reverse

from notifications.models import Notification
from onedollar_backend.settings_local import MEDIA_URL
from models import *
from django.conf import settings
from django.db.models import Count
from django.utils.timesince import timesince
from django.utils import timezone
from django.utils.text import ugettext_lazy as _
from datetime import timedelta

from django_redis import get_redis_connection
import stripe

from unify_django import api_utils
import payment


def calc_timesince(value):
    try:
        difference = timezone.now() - value
        if difference < timedelta(minutes=1):
            return 'just now'

        return u'{} ago'.format(timesince(value).split(', ')[0])
    except Exception as e:
        return u'just now'


class HyperlinkedFileField(serializers.FileField):
    def to_representation(self, value):
        request = self.context.get('request', None)
        if value and value.name:
            if request == None:
                from unify_django.middlewares import ThreadLocal
                request = ThreadLocal.get_current_request()

            if request != None:
                return request.build_absolute_uri(value.url)
        return ''


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('id', 'name', 'currency_code')


class LiteUserSerializer(serializers.ModelSerializer):
    uri = serializers.SerializerMethodField('_uri')
    country = CountrySerializer()
    
    def _uri(self, obj):
        return reverse('users-detail', kwargs={'pk': obj.id})

    class Meta:
        model = OneDollarUser
        fields = ('id', 'uri', 'username', 'email', 'first_name', 'last_name', 'avatar', 'phone',
                  'street1', 'street2', 'postal_code', 'province', 'city', 'country')


class BasicUserSerializer(serializers.ModelSerializer):
    uri = serializers.SerializerMethodField('_uri')
    credits = serializers.SerializerMethodField('_total_credits')
    country = CountrySerializer(read_only=True)
    country_id = serializers.IntegerField()

    def _uri(self, obj):
        return reverse('users-detail', kwargs={'pk': obj.id})

    def _total_credits(self, obj):
        return obj.total_credits

    class Meta:
        model = OneDollarUser
        fields = ('id', 'uri', 'email', 'first_name', 'last_name', 'username',
                  'gender', 'about', 'avatar', 'phone', 'credits',
                  'relationship_status', 'likes_count', 'dislikes_count',
                  'street1', 'street2', 'postal_code', 'province', 'city',
                  'winners_count', 'product_listing_count', 'country_id')


class UserSerializer(BasicUserSerializer):
    country = CountrySerializer(read_only=True)
    creation_date = serializers.DateTimeField(format='%m/%d/%Y', input_formats=['%m/%d/%Y'], read_only=True)

    class Meta(BasicUserSerializer.Meta):
        fields = BasicUserSerializer.Meta.fields + ('country', 'creation_date', 'fb_uid', 'gp_uid',
                'is_email_verified', 'is_recharged','is_phone_verified',
                'is_staff','is_payment_verified','is_accept_terms_of_service',
                'is_create_product',)



class UserWithTokenSerializer(UserSerializer):
    token = serializers.CharField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('token', 'is_staff', 'referral_code',)


class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = OneDollarUser
        fields = ('username', 'email', 'country', 'password', 'avatar', 'platform', 'deviceID')

    def create(self, validated_data):
        if validated_data.has_key('password'):
            user = OneDollarUser()
            user.set_password(validated_data['password'])
            validated_data['password'] = user.password
        return super(UserSignupSerializer, self).create(validated_data)

# For merchants
class MerchantsSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = OneDollarUser
        fields = ('username', 'email', 'country', 'password')

    def create(self, validated_data):
        if validated_data.has_key('password'):
            user = OneDollarUser()
            user.set_password(validated_data['password'])
            validated_data['password'] = user.password
            validated_data['platform'] = 'Web'
            validated_data['is_staff'] = True
        return super(MerchantsSignupSerializer, self).create(validated_data)


class CategorySerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField('_type')

    class Meta:
        model = Category
        fields = ('id', 'name', 'type')

    def _type(self, obj):
        return 'bet' if obj.type == Category.TYPE_BET else 'shop'

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand



class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPhoto
        fields = ('id', 'image',)

# other-user-pet-on
class ProductOtherUserPetOnSerializer(serializers.ModelSerializer):
    creator = LiteUserSerializer(required=False, read_only=True)
    photos = PhotoSerializer(many=True, read_only=True)
    current_user_bets = serializers.SerializerMethodField('get_current_user_product_bet_list')
    category = serializers.StringRelatedField()
    creation_date = serializers.DateTimeField(format='%m/%d/%Y', input_formats=['%m/%d/%Y'], read_only=True)
    creation_date_text = serializers.SerializerMethodField('_creation_date_text')
    winner = LiteUserSerializer(required=False, read_only=True)
    sold_tickets = serializers.IntegerField(read_only=True)
    end_date = serializers.DateTimeField(format='%m/%d/%Y', input_formats=['%m/%d/%Y'], read_only=True)
    no_of_days = serializers.IntegerField(read_only=True)
    is_sponsored = serializers.BooleanField(read_only=True)
    created_this_week = serializers.SerializerMethodField('_created_this_week')
    latest_bet_date_text = serializers.SerializerMethodField('_latest_bet_date_text')
    price = serializers.SerializerMethodField('_price')
    colors = fields.MultipleChoiceField(choices=('',))
    sizes = fields.MultipleChoiceField(choices=('',))

    class Meta:
        model = Product
        fields = ('id', 'title', 'category', 'description', 'no_of_days', 'end_date', 'end_date_countdown',
                  'is_new', 'created_this_week', 'quantity', 'price', 'ticket_price', 'retail_price', 
                  'sold_tickets', 'total_tickets', 'creator', 'photos', 'colors', 'sizes',
                  'winner', 'win_number', 'current_user_bets', 'creation_date', 'creation_date_text',
                  'location_id', 'location_name', 'location_address', 'location_city', 'location_state', 
                  'location_country', 'location_lat', 'location_lng', 'latest_chat_date', 'is_sponsored',
                  'should_display_winner_popup', 'should_display_seller_popup', 'latest_bet_date_text')

    def _price(self, obj):
        return obj.quantity

    def _created_this_week(self, obj):
        return (timezone.now() - obj.creation_date).days < 7

    def _creation_date_text(self, obj):
        return calc_timesince(obj.creation_date)

    def get_current_user_product_bet_list(self, obj):
        user = self.context['request'].user

        if not user.is_authenticated():
            return []

        return Bet.objects.filter(product=obj, user=user).values_list('number', flat=True)

    def _latest_bet_date_text(self, obj):
        bet = obj.bets.filter(user=self.context['request'].user).order_by('-creation_date').first()

        if bet:
            return calc_timesince(bet.creation_date)
        
        return  None

    def create(self, validated_data):
        request = self.context['request']
        validated_data['creator'] = request.user
        return super(ProductSerializer, self).create(validated_data)

    def save(self, **kwargs):
        request = self.context['request']

        category = request.DATA.get('category', None)
        if category:
            kwargs['category_id'] = category

        product = super(ProductSerializer, self).save(**kwargs)
        product.country.add(request.user.country)

        photos = self.initial_data.getlist('photos')
        product_photos = []
        for photo in photos:
            product_photo = ProductPhoto(product=product)
            product_photo.image.save(photo.name, photo)

        product.generate_tickets()

        return product

class ProductSerializer(serializers.ModelSerializer):
    view = serializers.SerializerMethodField('_get_view_count')
    creator = LiteUserSerializer(required=False, read_only=True)
    photos = PhotoSerializer(many=True, read_only=True)
    current_user_bets = serializers.SerializerMethodField('get_current_user_product_bet_list')
    category = serializers.StringRelatedField()
    creation_date = serializers.DateTimeField(format='%m/%d/%Y %H:%M:%S', input_formats=['%m/%d/%Y %H:%M:%S'], read_only=True)
    creation_date_text = serializers.SerializerMethodField('_creation_date_text')
    winner = LiteUserSerializer(required=False, read_only=True)
    sold_tickets = serializers.IntegerField(read_only=True)
    end_date = serializers.DateTimeField(format='%m/%d/%Y %H:%M:%S', input_formats=['%m/%d/%Y %H:%M:%S'], read_only=True)
    no_of_days = serializers.IntegerField(read_only=True)
    is_sponsored = serializers.BooleanField(read_only=True)
    created_this_week = serializers.SerializerMethodField('_created_this_week')
    latest_bet_date_text = serializers.SerializerMethodField('_latest_bet_date_text')
    price = serializers.SerializerMethodField('_price')
    colors = fields.MultipleChoiceField(choices=('',))
    sizes = fields.MultipleChoiceField(choices=('',))

    class Meta:
        model = Product
        fields = ('id', 'title', 'category', 'description', 'no_of_days', 'end_date', 'end_date_countdown',
                  'is_new', 'created_this_week', 'quantity', 'price', 'ticket_price', 'retail_price', 
                  'sold_tickets', 'total_tickets', 'creator', 'photos', 'colors', 'sizes',
                  'winner', 'win_number', 'current_user_bets', 'creation_date', 'creation_date_text',
                  'location_id', 'location_name', 'location_address', 'location_city', 'location_state', 
                  'location_country', 'location_lat', 'location_lng', 'latest_chat_date', 'is_sponsored',
                  'should_display_winner_popup', 'should_display_seller_popup', 'latest_bet_date_text','view',
                  'win_second','win_third', 'win_second_number','win_third_number','win_second_award','win_third_award')

    def _price(self, obj):
        return obj.quantity

    def _get_view_count(self, obj):
        # print obj.id
        productcount = ProductCount.objects.filter(product=obj).first()
        if productcount:
            row=ProductCount.objects.filter(product=obj).first()
            row.count=row.count+1
            row.save()
            return row.count
        else:
            row=ProductCount(product = obj, count = 1)
            row.save()
            return row.count

    def _created_this_week(self, obj):
        return (timezone.now() - obj.creation_date).days < 7

    def _creation_date_text(self, obj):
        return calc_timesince(obj.creation_date)

    def get_current_user_product_bet_list(self, obj):
        user = self.context['request'].user

        if not user.is_authenticated():
            return []

        return Bet.objects.filter(product=obj, user=user).values_list('number', flat=True)

    def _latest_bet_date_text(self, obj):
        bet = obj.bets.filter(user=self.context['request'].user).order_by('-creation_date').first()

        if bet:
            return calc_timesince(bet.creation_date)
        
        return  None

    def create(self, validated_data):
        request = self.context['request']
        validated_data['creator'] = request.user
        return super(ProductSerializer, self).create(validated_data)

    def save(self, **kwargs):
        request = self.context['request']

        category = request.DATA.get('category', None)
        if category:
            kwargs['category_id'] = category

        product = super(ProductSerializer, self).save(**kwargs)
        product.country.add(request.user.country)

        photos = self.initial_data.getlist('photos')
        product_photos = []
        for photo in photos:
            product_photo = ProductPhoto(product=product)
            product_photo.image.save(photo.name, photo)

        product.generate_tickets()

        return product


class BetSerializer(serializers.ModelSerializer):
    number = serializers.IntegerField(required=False, read_only=True)
    updated_credits = serializers.SerializerMethodField('_updated_credits')
    sold_tickets = serializers.SerializerMethodField('_sold_tickets')

    def _updated_credits(self, obj):
        try:
            return float("{0:.2f}".format(OneDollarUser.objects.filter(pk=self.context['request'].user.id).first().total_credits) )
        except Exception as e:
            return 0

    def _sold_tickets(self, obj):
        try:
            return obj.product.sold_tickets
        except Exception as e:
            return 0

    class Meta:
        model = Bet
        fields = ('product', 'number', 'updated_credits', 'sold_tickets')


class BetFullSerializer(serializers.ModelSerializer):
    user = LiteUserSerializer()
    creation_date = serializers.DateTimeField(format='%m/%d/%Y')
    creation_date_text = serializers.SerializerMethodField('_creation_date_text')
    product_title = serializers.SerializerMethodField('_product_title')
    class Meta:
        model = Bet

    def _creation_date_text(self, obj):
        return calc_timesince(obj.creation_date)

    def _product_title(self, obj):
        return obj.product.title

# other-users-bet-on        
class OtherUserBetOnSerializer(serializers.ModelSerializer):
    # user = LiteUserSerializer()
    # creation_date = serializers.DateTimeField(format='%m/%d/%Y')
    # creation_date_text = serializers.SerializerMethodField('_creation_date_text')

    class Meta:
        model = Bet
        # fields = ('user')

    def _creation_date_text(self, obj):
        return calc_timesince(obj.creation_date)


class RatingSerializer(serializers.ModelSerializer):
    is_created = serializers.SerializerMethodField('_is_created')
    creation_date = serializers.DateTimeField(format='%m/%d/%Y', input_formats=['%m/%d/%Y'])
    creation_date_text = serializers.SerializerMethodField('_creation_date_text')

    class Meta:
        model = OneDollarUserRating
        fields = ('rating_from', 'rating_to', 'rating_type', 'comment', 'is_created', 'creation_date', 'creation_date_text')

    def _is_created(self, obj):
        return not self._already_exists

    def _creation_date_text(self, obj):
        return calc_timesince(obj.creation_date)

    def is_valid(self, raise_exception=False):
        self._already_exists = False
        if self.initial_data:
            try:
                rating_from = self.initial_data.get('rating_from', self.context['request'].user.id)
                self.instance = self.Meta.model.objects.get(
                                    rating_from=rating_from,
                                    rating_to=self.initial_data.get('rating_to', None),
                                    rating_type=self.initial_data.get('rating_type', None)
                                )
                self._validated_data = {
                    'rating_from': self.instance.rating_from, 
                    'rating_to': self.instance.rating_to,
                    'rating_type': self.instance.rating_type,
                    'comment': self.instance.comment
                }
                self._errors = {}
                self._already_exists = True

                return True
            except self.Meta.model.DoesNotExist:
                pass

        return super(RatingSerializer, self).is_valid(raise_exception=True)


class RatingListSerializer(serializers.ModelSerializer):
    rating_from = BasicUserSerializer()
    creation_date = serializers.DateTimeField(format='%m/%d/%Y', input_formats=['%m/%d/%Y'])
    creation_date_text = serializers.SerializerMethodField('_creation_date_text')

    class Meta:
        model = OneDollarUserRating
        fields = ('rating_from', 'rating_to', 'rating_type', 'comment', 'creation_date', 'creation_date_text')

    def _creation_date_text(self, obj):
        return calc_timesince(obj.creation_date)


class CommentSerializer(serializers.Serializer):
    id = serializers.CharField()
    user = serializers.IntegerField(required=False, default=None)
    comment = serializers.CharField()
    creation_date = serializers.DateTimeField()
    to_user = serializers.IntegerField(required=False, default=None)
    product = serializers.IntegerField(required=False, default=None)


class NotificationSerializer(serializers.ModelSerializer):
    actor = LiteUserSerializer()
    product_id = serializers.SerializerMethodField('_product_id')
    product_image = serializers.SerializerMethodField('_product_image')
    product_countries = serializers.SerializerMethodField('_product_countries')
    timestamp_text = serializers.SerializerMethodField('_timestamp_text')

    def _timestamp_text(self, obj):
        return calc_timesince(obj.timestamp)

    def _product_id(self, obj):
        return obj.target_object_id

    def _product_countries(self, obj):
        return Country.objects.filter(product=obj.target_object_id).values_list('id', flat=True)

    def _product_image(self, obj):
        if obj.verb.startswith('has won'):
            product_photo = ProductPhoto.objects.filter(product_id=obj.target_object_id).first()

            if product_photo:
                return product_photo.image.url

        return None

    class Meta:
        model = Notification
        fields = ('id', 'unread', 'actor', 'verb', 'product_id', 'product_image', 'product_countries', 'timestamp', 'timestamp_text')


class TransactionSerializer(serializers.ModelSerializer):
    creation_date_text = serializers.SerializerMethodField('_creation_date_text')
    amount = serializers.IntegerField(read_only=True)

    def _creation_date_text(self, obj):
        return calc_timesince(obj.creation_date)

    class Meta:
        model = Transaction
        fields = ('amount', 'paypal_id', 'updated_credits', 'transaction_type', 'creation_date', 'creation_date_text')

    updated_credits = serializers.SerializerMethodField('_updated_credits')

    def _updated_credits(self, obj):
        try:
            return OneDollarUser.objects.filter(pk=self.context['request'].user.id).first().total_credits
        except Exception as e:
            return 0

    def create(self, validated_data):
        transaction_type = validated_data.get('transaction_type', None)
        if transaction_type == Transaction.TYPE_REWARD:
            if Transaction.objects.filter(transaction_type=Transaction.TYPE_REWARD, \
                    user=self.context['request'].user).first():
                raise api_utils.BadRequest('ALREADY_REWARDED')

            validated_data['amount'] = 1
        elif transaction_type == Transaction.TYPE_REWARD_LIKE:
            if Transaction.objects.filter(transaction_type=Transaction.TYPE_REWARD_LIKE, \
                    user=self.context['request'].user).first():
                raise api_utils.BadRequest('ALREADY_REWARDED')

            validated_data['amount'] = 1
        elif transaction_type == Transaction.TYPE_REWARD_RATE:
            if Transaction.objects.filter(transaction_type=Transaction.TYPE_REWARD_RATE, \
                    user=self.context['request'].user).first():
                raise api_utils.BadRequest('ALREADY_REWARDED')

            validated_data['amount'] = 1
        elif transaction_type == Transaction.TYPE_TOPUP:
            token = self.context['request'].data.get('token', None)
            package_id = self.context['request'].data.get('package_id', None)
            user = self.context['request'].user

            if token and package_id:
                try:
                    package = TopupPackage.objects.filter(pk=package_id, type=TopupPackage.TYPE_STRIPE).first()

                    if not package:
                        raise api_utils.BadRequest('INVALID_PACKAGE')

                    if Transaction.objects.filter(paypal_id=token).first():
                        raise api_utils.BadRequest('TOKEN_EXISTS')

                    amount = package.topup_value*100
                    currency = user.country.currency_code

                    stripe_payment = payment.StripePayment()
                    charge = stripe_payment.charge(amount=amount, currency=currency, token=token)
                    
                    validated_data['paypal_id'] = token
                    validated_data['transaction_id'] = charge.id
                    validated_data['transaction_type'] = Transaction.TYPE_TOPUP
                    validated_data['amount'] = package.credits
                    validated_data['money'] = package.topup_value
                    validated_data['user'] = user
                    validated_data['use_free_credit'] = False
                    validated_data['channel'] = Transaction.CHANNEL_STRIPE
                except payment.StripePayment.StripePaymentException:
                    raise api_utils.BadRequest('STRIPE_ERROR')
                except Exception as e:
                    raise api_utils.BadRequest(e.message)
            else:
                paypal = payment.PayPalPayment(
                    mode=settings.PAYPAL_MODE,
                    client_id=settings.PAYPAL_CLIENT_ID,
                    client_secret=settings.PAYPAL_CLIENT_SECRET
                )

                paypal_id = validated_data.get('paypal_id')
                if Transaction.objects.filter(paypal_id=paypal_id).first():
                    raise api_utils.BadRequest('PAYPAL_ID_EXISTS')

                try:
                    receipt_data = paypal.verify_receipt(paypal_id)
                    transaction = receipt_data['transactions'][0]
                    related_resource = transaction['related_resources'][0]
                    payer = receipt_data['payer']['payer_info']

                    amount = transaction['amount']
                    amount = int(float(amount['total']))

                    package = TopupPackage.objects.filter(
                        topup_value=amount, type=TopupPackage.TYPE_PAYPAL).first()

                    if not package:
                        raise api_utils.BadRequest('INVALID_PACKAGE')

                    validated_data['amount'] = package.credits
                    validated_data['money'] = package.topup_value
                    validated_data['use_free_credit'] = False
                    validated_data['transaction_id'] = related_resource['sale']['id']
                    validated_data['channel'] = Transaction.CHANNEL_PAYPAL

                    if payer:
                        validated_data['payer_firstname'] = payer['first_name']
                        validated_data['payer_lastname'] = payer['last_name']
                        validated_data['payer_email'] = payer['email']
                except Exception as e:
                    print '>>>', e
                    raise api_utils.BadRequest('INVALID_PAYPAL_ID')
        else:
            raise api_utils.BadRequest('INVALID_TRANSACTION_TYPE')

        validated_data['user'] = self.context['request'].user
        return super(TransactionSerializer, self).create(validated_data)


class UserReportingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserReportingType


class ProductReportingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReportingType


class UserReportingSerializer(serializers.ModelSerializer):
    class Meta:
        model = OneDollarUser.reportings.through
        fields = ('user', 'report_type',)


class ProductReportingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product.reportings.through
        fields = ('product', 'report_type',)


class TopupPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopupPackage

class CatSpinSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCatSpin

class NotiSerializer(serializers.ModelSerializer):
    class Meta:
        model = WinnerProduct

class CategoryTestSerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField('_name')
    type = serializers.SerializerMethodField('_type')
    main_level = serializers.SerializerMethodField('_main')
    class Meta:
        model = CategoryTest

    def _name(self, obj):
        link = str(obj.get_absolute_url()).title()[1:]
        return link.replace("/", ", ")

    def _main(self, obj):
        link = str(obj.get_main_level()).title()[1:]
        return int(link)

    def _type(self, obj):
        return obj.get_type_display()
