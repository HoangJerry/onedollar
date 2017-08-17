# -*- encoding: utf8 -*-

import math, random, requests, os, re, ujson, StringIO
import datetime as dt
import redis
import hashlib
import facebook
import copy
from PIL import Image, ImageOps
from decimal import Decimal

from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.dispatch.dispatcher import receiver
from django.db.models import Count, Sum, F, Q, Case, When, Value, IntegerField
from django.db.models.signals import post_save, post_delete
from django.db.models.expressions import RawSQL
from django.db.utils import IntegrityError
from django_countries.fields import CountryField
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.text import slugify, capfirst
from django.core import mail
from django.core.urlresolvers import reverse
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.template.loader import render_to_string
from django.forms.widgets import SelectMultiple

from django_redis import get_redis_connection
from constance import config
from facepy import GraphAPI
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory, force_authenticate
from notifications import notify
from unify_django.models import *
from mailin import Mailin
from multiselectfield import MultiSelectField, MultiSelectFormField

from onedollar import tasks
from categories.base import CategoryBase
from django.utils.encoding import force_text

class CategoryTest(CategoryBase):
    TYPE_BET = 1
    TYPE_SHOP = 2
    CATEGORY_TYPES = (
        (TYPE_BET, _('Bet')),
        (TYPE_SHOP, _('Shop')),
    )
    type = models.PositiveSmallIntegerField(_('type'), choices=CATEGORY_TYPES, default=TYPE_BET)

    def get_absolute_url(self):
        """Return a path"""
        from django.core.urlresolvers import NoReverseMatch

        try:
            prefix = reverse('categories_tree_list')
        except NoReverseMatch:
            prefix = '/'
        ancestors = list(self.get_ancestors()) + [self, ]
        return prefix + '/'.join([force_text(i.name) for i in ancestors]) + '/'

    def get_main_level(self):
        from django.core.urlresolvers import NoReverseMatch

        try:
            prefix = reverse('categories_tree_list')
        except NoReverseMatch:
            prefix = '/'
        ancestors = list(self.get_ancestors()) + [self, ]
        return prefix + '/'.join([force_text(ancestors[0].id)])

class OneDollarUserManager(UnifyBaseUserManager):
    def get_or_create_user_from_googleplus(self, gp_token, default_username=None, default_email=None, should_create=True):
        UserModel = get_user_model()
        ret = False
        try:
            r = requests.get('https://www.googleapis.com/oauth2/v3/tokeninfo?id_token=' + gp_token)

            if r.status_code == 200:
                user = r.json()

                if user['aud'] not in [settings.ANDROID_CLIENT_ID, settings.IOS_CLIENT_ID, settings.WEB_CLIENT_ID]:
                    raise Exception("Unrecognized client.")

                email = user.get('email')
                username = email
                gp_uid = user.get('sub')
                first_name = user.get('given_name', '')
                last_name = user.get('family_name', '')
                gender = (user.get('gender', '') == 'male') \
                         and UserModel.CONST_GENDER_MALE or UserModel.CONST_GENDER_FEMALE
                relationship_status = ''
                about = ''
                dob = user.get('birthday', '')

                avatar_url = user.get('picture', '')

                try:
                    ret = self.get(gp_uid=gp_uid)
                except UserModel.DoesNotExist:
                    try:
                        ret = self.get(email=email)
                    except UserModel.DoesNotExist:
                        if not should_create:
                            return False
                        ret = self.create_user(username=username, email=email, commit=False)

                ret.gp_uid = gp_uid
                ret.gp_access_token = gp_token
                ret.is_email_verified = True

            ret = self.update_user_data(ret, username, email, first_name, last_name,
                                            gender, relationship_status, about, dob, avatar_url)

        except Exception as e:
            print ">>> get_or_create_user_from_googleplus ::", e

        return ret

    def get_or_create_user_from_facebook(self, fb_token, default_username=None, default_email=None, should_create=True):
        UserModel = get_user_model()
        ret = False
        try:
            graph = GraphAPI(fb_token)
            user = graph.get("me?fields=id,first_name,last_name,gender,relationship_status,bio,birthday,friends.limit(1000){id}")

            username = user.get('username', default_username)
            fb_uid = user.get('id')
            email = user.get('email', default_email and default_email or username)
            first_name = user.get('first_name', '')
            last_name = user.get('last_name', '')
            gender = (user.get('gender', '') == 'male') \
                     and UserModel.CONST_GENDER_MALE or UserModel.CONST_GENDER_FEMALE
            relationship_status = user.get('relationship_status')
            about = user.get('bio')
            dob = user.get('birthday', '')

            friends_count = 0
            friend_push_channels = None
            friends = user.get('friends', {})
            if friends:
                friends_count = friends.get('summary', {}).get("total_count", 0)
                friends_data = friends.get('data', [])

                if friends_data:
                    friend_fb_ids = [friend['id'] for friend in friends_data]
                    users = OneDollarUser.objects.filter(fb_uid__in=friend_fb_ids)
                    friend_push_channels = [user.push_channel for user in users]

            avatar_url = "http://graph.facebook.com/%s/picture?width=500&height=500&type=square" % fb_uid

            try:
                ret = self.get(fb_uid=fb_uid)
            except UserModel.DoesNotExist:
                try:
                    ret = self.get(email=email)
                except UserModel.DoesNotExist:
                    if not should_create:
                        return False
                    ret = self.create_user(username=username, email=email, commit=False)
                    
                    if ret and friend_push_channels != None:
                        tasks.send_pushnotifs(friend_push_channels, {
                            'body': u'{} {} joined OneDollar'.format(first_name, last_name),
                        })

            ret.fb_uid = fb_uid
            ret.fb_access_token = fb_token
            ret.is_email_verified = True

            ret = self.update_user_data(ret, username, email, first_name, last_name,
                                        gender, relationship_status, about, dob, avatar_url, friends_count)
        except Exception as e:
            print ">>> get_or_create_user_from_facebook ::", e
            pass

        return ret

    def update_user_data(self, user, username, email, first_name,
                         last_name, gender, relationship_status, about, dob, avatar_url, friends_count=0):
        UserModel = get_user_model()
        if user.pk == None:
            if user.email == '':
                user.email = email

            if user.username == '':
                user.username = username

            if not user.first_name:
                user.first_name = first_name

            if not user.last_name:
                user.last_name = last_name

            if not user.pk:
                user.gender = gender

            if not user.relationship_status and relationship_status:
                user.relationship_status = relationship_status

            if not user.about and about:
                user.about = about

            if dob and not user.dob:
                user.dob = dt.datetime.strptime(dob, '%m/%d/%Y')

            user.is_active = True
            user.status = UserModel.CONST_STATUS_ENABLED

        if not user.avatar and user.pk == None:
            avatar_stream = urlopen(avatar_url)
            user.avatar.save(slugify(user.username + " social") + '.jpg',
                             ContentFile(avatar_stream.read()))

        user.friends_count = friends_count

        user.save()
        
        return user

    def get_users_not_use_free_dollar(self):
        qs = self.get_queryset()
        d = dt.datetime.now() - dt.timedelta(days=7)
        qs = qs.annotate(num_bets=Count('bets')) \
            .filter(creation_date__startswith=d.date(), num_bets=0)
        return qs


class OneDollarUser(UnifyBaseUser):
    credits = models.FloatField(_('credits'), default=0)
    free_credits = models.FloatField(_('free credits'), default=1)
    country = models.ForeignKey('Country')
    creation_date = models.DateTimeField(auto_now_add=True)
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    is_payment_verified = models.BooleanField(default=False)
    is_accept_terms_of_service = models.BooleanField(default=False)
    is_recharged = models.BooleanField(default=False)
    is_create_product = models.BooleanField(default=False)
    bets = models.ManyToManyField('Product', through='Bet')
    phone = models.CharField(max_length=20, null=True, blank=True)
    reportings = models.ManyToManyField('UserReportingType', through='UserReporting', through_fields=('user', 'report_type',))
    street1 = models.CharField(max_length=300, null=True, blank=True)
    street2 = models.CharField(max_length=300, null=True, blank=True)
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    friends_count = models.IntegerField(_('friends count'), default=0)
    sms_count = models.IntegerField(_('sms count'), default=0)
    aggregated_topups = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    platform = models.CharField(max_length=10, null=True, blank=True)
    deviceID = models.CharField(max_length=100, null=True, blank=True)
    referral_code = models.CharField(max_length=50, null=True, blank=True)
    referrer = models.ForeignKey('OneDollarUser', related_name='referee', null=True, blank=True)
    receive_bonus = models.BooleanField(default=False)
    is_flagged = models.BooleanField(default=False)

    objects = OneDollarUserManager()
    user_stats = None

    second_chance_4h_48h = models.IntegerField(default=0)
    enter_his_address_after_8h_48h = models.IntegerField(default=0)
    collect_your_cash_4h_24h = models.IntegerField(default=0)

    total_order = models.IntegerField(default=0)
    def __unicode__(self):
        ret = self.email
        if self.first_name and self.last_name:
            ret = u'{} {}'.format(self.first_name, self.last_name)
        return ret

    @property
    def fblink(self):
        if self.fb_uid:
            return mark_safe('<a target="_blank" href="https://fb.com/{fb_uid}">{fb_uid}</a>'.format(fb_uid=self.fb_uid))
        return None
    
    @property
    def edit_link(self):
        return mark_safe('<a href="{url}" target="_blank">{email}<a/>'.format(
            url=reverse('admin:onedollar_onedollaruser_change', args=[self.id]), email=self.email))

    @property
    def address(self):
        ret = filter(lambda x: x != None and x != '', 
                [self.street1, self.street2, self.postal_code, self.province, self.city, self.phone])
        return '<br />'.join(ret)

    @property
    def full_address(self):
        ret = filter(lambda x: x != None and x != '', 
                [self.first_name, self.last_name, self.street1, self.street2, 
                    self.postal_code, self.province, self.city, self.country.name, self.phone])

        ret.insert(0, self.edit_link)

        if self.fb_uid:
            ret.append('<a href="https://facebook.com/{fb_uid}" target="_blank">fb: {fb_uid}</a>'.format(fb_uid=self.fb_uid))

        return '<br />'.join(ret)

    @property
    def is_verified(self):
        return self.fb_uid != None or self.gp_uid != None or self.is_email_verified

    @property
    def total_credits(self):
        return self.credits + self.free_credits

    @property
    def activity_notification_key(self):
        return '{}_notification_activity'.format(self.id)

    @property
    def chat_notification_key(self):
        return '{}_notification_chat'.format(self.id)

    @property
    def common_notification_key(self):
        return '{}_notification_common'.format(self.id)

    def append_notification(self, notification_key, datetime_str):
        r = get_redis_connection()
        r.sadd(notification_key, datetime_str)

    @property
    def token(self):
        return self.auth_token.key

    def get_likes_dislikes_stats(self):
        self.user_stats = self.rating_to.aggregate(
            likes=Count(
                Case(When(rating_type=OneDollarUserRating.RATING_TYPE_LIKE, then=Value(1)), output_field=IntegerField())
            ),
            dislikes=Count(
                Case(When(rating_type=OneDollarUserRating.RATING_TYPE_DISLIKE, then=Value(1)), output_field=IntegerField())
            ),
        )

    @property
    def likes_count(self):
        if not self.user_stats:
            self.get_likes_dislikes_stats()
        return self.user_stats.get('likes', 0)

    @property
    def dislikes_count(self):
        if not self.user_stats:
            self.get_likes_dislikes_stats()
        return self.user_stats.get('dislikes', 0)

    @property
    def winners_count(self):
        return self.win_products.count()

    @property
    def product_listing_count(self):
        if hasattr(self, 'product__count'):
            return self.product__count
        return 0

    @property
    def push_channel(self):
        return self.id
    
    def update_aggregated_topups(self):
        ret = self.transaction_set.filter(transaction_type=Transaction.TYPE_TOPUP).aggregate(sum_topups=Sum('money'))
        self.aggregated_topups = int(ret['sum_topups'] or 0)
        self.save()

    @staticmethod
    def get_creation_stats():
        last_24_hours = timezone.now() - timezone.timedelta(hours=24)
        ret = OneDollarUser.objects.aggregate(
                total=Count('id'), 
                today=Count(
                    Case(
                        When(creation_date__gte=last_24_hours, then=Value(1)), 
                        output_field=IntegerField()
                    )
                ))
        return ret

    # Count User Flagged    
    @staticmethod
    def get_user_flagged_stats():
        ret = OneDollarUser.objects.aggregate(
                totalUserFlagged=Count(
                    Case(
                        When(is_flagged=1, then=Value(1)), 
                        output_field=IntegerField()
                    )
                ))
        return ret

    @property
    def claim_amounts(self):
        ret = self.product_set.aggregate(
            now=Sum(
                Case(When(Q(end_date__lte=timezone.now()-dt.timedelta(days=settings.DATE_CLAIM_MONEY_AFTER)) & Q(payout_date=None), then='sold_tickets'), output_field=IntegerField())
            ),
            later=Sum(
                Case(When(Q(end_date__gt=timezone.now()-dt.timedelta(days=settings.DATE_CLAIM_MONEY_AFTER)) & Q(payout_date=None), then='sold_tickets'), output_field=IntegerField())
            )
        )
        ret = {k: int((v or 0) * settings.PERCENT_CLAIM_PAYOUT * 100)/100.0 for k, v in ret.iteritems()}

        return ret

    @property
    def claim_products(self):
        return self.product_set.filter(
            Q(end_date__lte=timezone.now()-dt.timedelta(days=settings.DATE_CLAIM_MONEY_AFTER)) & Q(payout_date=None))

    def generate_referral_code(self):
        first_name = self.first_name or ''
        first_name = first_name.encode('ascii', 'ignore')
        last_name = self.last_name or ''
        last_name = last_name.encode('ascii', 'ignore')
        self.referral_code = slugify('{}-{}{}'.format(self.id, first_name, last_name))
        return self.referral_code

    def get_redirect_referral_link(self):
        return 'https://r56yg.app.goo.gl/?link={}referal/{}&apn=com.giinger.onedollar&ibi=com.giinger.onedollar'.format(settings.SITE_URL, self.referral_code)

    def get_short_referral_link(self):
        return reverse('referral-link', kwargs={'code': self.generate_referral_code()})

    def save(self, *args, **kwargs):
        ret = super(OneDollarUser, self).save(*args, **kwargs)

        if self.address:
            self.win_products.filter(delivery_status=Product.DELIVERY_STATUS_NEW).update(delivery_status=Product.DELIVERY_STATUS_PENDING)

        return ret

    def get_inprogress_bets(self):
        return Product.objects.raw('''
                select *
                from `onedollar_product` p
                join (
                    select product_id, max(id) mid
                    from `onedollar_bet`
                    where `onedollar_bet`.`user_id` = %s
                    group by product_id
                    order by mid desc) b on p.id = b.`product_id`
                where end_date > '{}' or end_date IS NULL
            '''.format(timezone.now().strftime('%Y-%m-%d %H:%M:%S'))
            , [self.id])


class OneDollarUserRating(models.Model):
    RATING_TYPE_LIKE = 1
    RATING_TYPE_DISLIKE = -1
    RATING_TYPES = (
        (RATING_TYPE_LIKE, 'Like'),
        (RATING_TYPE_DISLIKE, 'Dislike'),
    )

    rating_from = models.ForeignKey(OneDollarUser, related_name='rating_from')
    rating_to = models.ForeignKey(OneDollarUser, related_name='rating_to')
    comment = models.CharField(max_length=4000)
    rating_type = models.SmallIntegerField(choices=RATING_TYPES)
    creation_date = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('rating_from', 'rating_to', 'rating_type')


@receiver(post_save, sender=OneDollarUser)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
        instance.free_credits = config.THE_FREE_CREDITS_GIVEN

        if instance.referrer_id:
            instance.free_credits += config.REFERRAL_AMOUNT

        instance.generate_referral_code()
        instance.save()

        if instance.email:
            # subject = 'OneDollar – Bet, win and grab your prize'
            # html_content = render_to_string('email/welcome.html', {'name': instance.first_name})
            # tasks.send_email(subject, html_content, [instance.email])
            m = Mailin("https://api.sendinblue.com/v2.0","yA3MRfQW9wv0jTZp")
            data = {
                "email" : instance.email,
                "attributes" : {"NAME": instance.first_name, "SURNAME": instance.last_name}, 
                "listid" : [5]
            }
            m.create_update_user(data)


class OneDollarUserToken(models.Model):
    token = models.CharField(max_length=200, unique=True)
    user = models.ForeignKey(OneDollarUser, null=True, blank=True)

    @staticmethod
    def get_tokens_of_users(user_ids):
        return OneDollarUserToken.objects.filter(user__in=user_ids).values_list('token', flat=True)


class Category(BaseModelMixin):
    TYPE_BET = 1
    TYPE_SHOP = 2
    CATEGORY_TYPES = (
        (TYPE_BET, _('Bet')),
        (TYPE_SHOP, _('Shop')),
    )

    name = models.CharField(_('name'), max_length=50)
    type = models.PositiveSmallIntegerField(_('type'), choices=CATEGORY_TYPES, default=TYPE_BET)

    class Meta:
        verbose_name_plural = _('categories')

    def __unicode__(self):
        return self.name

class Brand(models.Model):
    name = models.CharField(_('name'), max_length=50)

    def __unicode__(self):
        return self.name

        

class WinnerProduct(models.Model):
    product = models.IntegerField(null=True, blank=True)
    win1 = models.IntegerField(null=True, blank=True)
    win2 = models.IntegerField(null=True, blank=True)
    win3 = models.IntegerField(null=True, blank=True)

class Product(models.Model):
    DELIVERY_STATUS_NEW = 0
    DELIVERY_STATUS_PENDING = 10
    DELIVERY_STATUS_SENT = 20
    DELIVERY_STATUS_NOREPLY = 30
    DELIVERY_STATUS_NOADDRESS = 40
    DELIVERY_STATUS_BLOCKEDORFRAUD= 50
    DELIVERY_STATUSES = (
        (DELIVERY_STATUS_NEW, _("New")),
        (DELIVERY_STATUS_PENDING, _("Pending")),
        (DELIVERY_STATUS_SENT, _("Sent")),
        (DELIVERY_STATUS_NOREPLY, _("Not sent (no reply)")),
        (DELIVERY_STATUS_NOADDRESS, _("Not sent (no address)")),
        (DELIVERY_STATUS_BLOCKEDORFRAUD, _("Blocked or Fraud")),
    )

    DRAWING_METHOD_RANDOM = 0
    DRAWING_METHOD_FB_FRIENDS = 1
    DRAWING_METHOD_MOST_TOPUP = 2
    DRAWING_METHOD_CHEAT = 3
    DRAWING_METHODS = (
        (DRAWING_METHOD_RANDOM, _("Random")),
        (DRAWING_METHOD_FB_FRIENDS, _("FB Friends")),
        (DRAWING_METHOD_MOST_TOPUP, _("Most Topups")),
        (DRAWING_METHOD_CHEAT, _("Cheat mode")),
    )

    STATUS_DISABLE = 0
    STATUS_ENABLE = 10
    STATUSES = (
        (STATUS_DISABLE, _("Disable")),
        (STATUS_ENABLE, _("Enable")),
    )

    COLORS = (('white', 'White'),
              ('green', 'Green'),
              ('beige', 'Beige'),
              ('ivory', 'Ivory'),
              ('black', 'Black'),
              ('grey', 'Grey'),
              ('pink', 'Pink'),
              ('navyblue', 'Navy Blue'),
              ('red', 'Red'),
              ('brown', 'Brown'),
              ('orange', 'Orange'),
              ('purple', 'Purple'),
              ('blue', 'Blue'),
              ('tan', 'Tan'),
              ('yellow', 'Yellow'),
              ('gold', 'Gold'),
              ('multicolor', 'Multicolor'))

    SIZES = (('xxs', 'XXS'),
             ('xs', 'XS'),
             ('s', 'S'),
             ('m', 'M'),
             ('l', 'L'),
             ('xl', 'XL'),
             ('xxl', 'XXL'),
             ('xxxl', 'XXXL'))

    creation_date = models.DateTimeField()
    modification_date = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, editable=False)
    status = models.SmallIntegerField(choices=STATUSES, default=STATUS_DISABLE)
    is_sponsored = models.BooleanField(default=False)
    category = models.ForeignKey(Category, null=True, blank=True)
    title = models.CharField(_('title'), max_length=200)
    description = models.TextField(_('description'))
    no_of_days = models.PositiveSmallIntegerField(_('Number of hours:'), null=True, blank=True)
    sold_tickets = models.IntegerField(_('sold tickets'), default=0)
    end_date = models.DateTimeField(_('end date'), null=True, blank=True)
    is_new = models.BooleanField(_('This is a new product'))
    quantity = models.IntegerField(_('Ticket quantity'), default=0)
    retail_price = models.IntegerField(_('Retail Price'), null=True, blank=True)
    ticket_price = models.DecimalField(_('Ticket price per unit'), default=1, decimal_places=2, max_digits=5)
    winner = models.ForeignKey(OneDollarUser, related_name='win_products', null=True, blank=True)
    win_number = models.IntegerField(null=True, blank=True, help_text=_('Make sure that you only edit this field for cheat mode only!!! If the result is already drawn, changing the win number may cause issues'))
    reportings = models.ManyToManyField('ProductReportingType', through='ProductReporting')
    location_id = models.CharField(max_length=50, help_text=mark_safe(_(
        'To get Foursqure Location ID, visit <a target="_blank" href="https://foursquare.com/">https://foursquare.com/'
        '</a> to search for a location and open the location page with URL like '
        '<a target="_blank" href="https://foursquare.com/v/starbucks-coffee--new-world-hotel/50ae4436e4b04c937a56de9c">'
        'https://foursquare.com/v/starbucks-coffee--new-world-hotel/50ae4436e4b04c937a56de9c</a>.\n'
        'The ID is the last part of the URL, ie. 50ae4436e4b04c937a56de9c')), null=True, blank=True)
    location_name = models.CharField(max_length=100, null=True, blank=True)
    location_address = models.CharField(max_length=400, null=True, blank=True)
    location_city = models.CharField(max_length=100, null=True, blank=True)
    location_state = models.CharField(max_length=100, null=True, blank=True)
    location_country = models.CharField(max_length=100, null=True, blank=True)
    location_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    payout_date = models.DateTimeField(_('payout_date'), null=True, blank=True)
    latest_chat_date = models.DateTimeField(_('latest_chat_date'), null=True, blank=True, editable=False)
    country = models.ManyToManyField('Country')
    delivery_status = models.SmallIntegerField(choices=DELIVERY_STATUSES, default=DELIVERY_STATUS_NEW)
    ordering_date = models.DateField(null=True, blank=True)
    ordering_tracking = models.CharField(null=True, blank=True, max_length=1000)
    cost = models.FloatField(_('COP'), default=0)
    drawing_method = models.SmallIntegerField(choices=DRAWING_METHODS, default=DRAWING_METHOD_RANDOM)
    from_shop = models.CharField(_('From'), max_length=100, null=True, blank=True)
    should_display_winner_popup = models.BooleanField(default=True)
    should_display_seller_popup = models.BooleanField(default=True)
    colors = MultiSelectField(choices=COLORS, null=True, blank=True)
    sizes = MultiSelectField(choices=SIZES, null=True, blank=True)
    product_quantity = models.PositiveSmallIntegerField(default=0)
    iteration = models.PositiveSmallIntegerField(default=0)
    waiting_time = models.PositiveIntegerField(default=5)
 
    win_second = models.ForeignKey(OneDollarUser, related_name='win_second', null=True, blank=True)
    win_third = models.ForeignKey(OneDollarUser, related_name='win_third', null=True, blank=True)
    win_second_number = models.IntegerField(null=True, blank=True, help_text=_('Make sure that you only edit this field for cheat mode only!!! If the result is already drawn, changing the win number may cause issues'))
    win_third_number = models.IntegerField(null=True, blank=True, help_text=_('Make sure that you only edit this field for cheat mode only!!! If the result is already drawn, changing the win number may cause issues'))
    win_second_award = models.DecimalField(max_digits=9, decimal_places=3, null=True, blank=True,default=1)
    win_third_award = models.DecimalField(max_digits=9, decimal_places=3, null=True, blank=True,default=0.5)

    showable = BaseModelMixinManager()
    objects = models.Manager()
    _default_manager = objects

    def __unicode__(self):
        return self.title

    def __init__(self, *args, **kwargs):
        super(Product, self).__init__(*args, **kwargs)
        self.initial_quantity = self.quantity if self.id else 0

    @property
    def product_edit_url(self):
        return u'<a href="{}" target="_blank">{}</a>'.format(reverse('admin:onedollar_product_change', args=[self.id]),
                                            self.title)

    @property
    def product_tickets_key(self):
        return '{}_tickets'.format(self.id)

    @property
    def product_tickets_progress_key(self):
        return self.product_tickets_key + '_progress'

    @property
    def total_tickets(self):
        return self.quantity

    @property
    def end_date_countdown(self):
        if self.end_date:
            return max((self.end_date - timezone.now()).days, 0)
        return None

    @property
    def pl_value(self):
        return self.sold_tickets-self.cost
    
    @property
    def winner_address(self):
        if self.winner:
            return self.winner.address
        return ''  

    @property
    def winner_second_address(self):
        if self.win_second:
            return self.win_second.address
        return ''    
    @property

    def winner_third_address(self):
        if self.win_third:
            return self.win_third.address
        return ''

    @property
    def winner_full_address(self):
        if self.winner:
            return self.winner.full_address
        return ''

    @property
    def winner_second_full_address(self):
        if self.win_second:
            return self.win_second.full_address
        return ''

    @property
    def winner_third_full_address(self):
        if self.win_third:
            return self.win_third.full_address
        return ''

    @property
    def winner_fbuid(self):
        if self.winner:
            return self.winner.fb_uid
        return ''
    
    @property
    def countries(self):
        return '<br />'.join(self.country.all().values_list('name', flat=True))
    
    def share_to_facebook(self, token):
        fb_data = {
            "description": "Congratulations! {} bet smart on this product. #onedollarapp #onedollar".format(\
                    self.winner.get_full_name().encode('utf8')),
            "name": self.title.encode('utf8'),
            "link": settings.ONEDOLLAR_BIZ_URL,
        }

        photo = self.photos.first()
        photo_url = None
        if photo:
            thumb_size = (700,368)

            photo_name = 'overlay/product{}_photo{}_w{}_h{}.jpg'.format(self.id, photo.id, *thumb_size)
            photo_location = os.path.join(settings.MEDIA_ROOT, photo_name)
            photo_url = settings.MEDIA_URL+photo_name

            if not os.path.exists(photo_location):
                canvas = Image.new('RGBA', thumb_size, (255,255,255,255))
                watermark = Image.open('watermark.png')
                image = Image.open(photo.image)
                image.thumbnail(thumb_size)

                bg_w, bg_h = canvas.size
                img_w, img_h = image.size
                offset = ((bg_w - img_w) / 2, (bg_h - img_h) / 2)

                canvas.paste(image, offset)
                canvas.paste(watermark, (0,0), watermark)

                canvas.save(photo_location)

            fb_data['picture'] = photo_url

        graph = facebook.GraphAPI(token)
        graph.put_wall_post(
            '',
            fb_data
        )

    def save(self, *args, **kwargs):
        is_created = False
        if self.pk is None:
            is_created = True
            self.status = self.STATUS_ENABLE

        if is_created:
            self.creation_date = self.creation_date or timezone.now()

        if self.winner == None and self.win_number == None:
            # only allow to change end_date before drawing
            if self.no_of_days:
                self.end_date = self.creation_date + dt.timedelta(hours=self.no_of_days)
                # self.end_date = self.end_date.replace(hour=23, minute=59, second=59)
            else:
                self.end_date = None

        if self.winner and self.winner.address:
            self.delivery_status = self.DELIVERY_STATUS_PENDING

        if self.ordering_date:
            self.delivery_status = self.DELIVERY_STATUS_SENT

        return super(Product, self).save(*args, **kwargs)

    def generate_tickets(self, force_generate=False):
        r = get_redis_connection()

        current_quantity = 0
        if not force_generate:
            current_quantity = self.initial_quantity

        tickets = range(current_quantity+1, self.quantity+1)
        #print current_quantity, self.quantity, self.product_tickets_key, tickets
        if len(tickets):
            r.sadd(self.product_tickets_key, *tickets)

    def buy_ticket(self, user, pay=1):
        r = get_redis_connection()
        bet = None
        # print "model testing       **"
            
        while True:
            ticket = r.srandmember(self.product_tickets_key)
            ret = None
            if ticket:
                # reserve the ticket
                ret = r.smove(self.product_tickets_key, self.product_tickets_progress_key, ticket)

            if ret:
                try:
                    # create ticket
                    bet = Bet.objects.create(number=ticket, user=user, product_id=self.id)
                except IntegrityError:
                    # the ticket has been used (integrity exception), just delete it
                    r.srem(self.product_tickets_progress_key, ticket)
                except:
                    # error occured, move the ticket back
                    # TODO consider if we may have ticket lost here
                    ret = r.smove(self.product_tickets_progress_key, self.product_tickets_key, ticket)
                    pass
                else:
                    # successful, safe to remove the resvered ticket
                    r.srem(self.product_tickets_progress_key, ticket)

                    self.sold_tickets = F('sold_tickets') + 1
                    self.save()
                    discount=1
                    if UserCatSpin.objects.filter(user=user):
                        usercat = UserCatSpin.objects.get(user=user)
                        discount =  1-usercat.discount 
                    if pay:
                        transaction = Transaction(
                            user=user,
                            amount=float(self.ticket_price) * -1 * discount,
                            transaction_type=Transaction.TYPE_BUY_TICKET,
                            bet=bet
                        )
                        transaction.save()

                    break
            else:
                # no more ticket number left
                break
        return bet

    def is_finished(self):
        return self.winner != None

    @staticmethod
    def get_due_products():
        return Product.objects.filter(Q(Q(sold_tickets__gte=F('quantity'), end_date=None) | Q(end_date__lte=timezone.now()), winner=None))

    @staticmethod
    def create_product_from_wish(wish_product_id, creator_id):
        ret = requests.get('https://www.wish.com/c/'+wish_product_id)

        if ret.status_code == 200:
            search = re.search(r"pageParams\[\'mainContestObj\'\] = (.*);", ret.content)

            if search and len(search.groups()) == 1:
                product_dict = ujson.loads(search.group(1))

                product = Product()
                product.creator_id = creator_id
                product.title = product_dict['name']
                product.price = product_dict['commerce_product_info']['variations'][0]['price']
                product.retail_price = product_dict['commerce_product_info']['variations'][0]['retail_price']
                product.cost = product.price + product_dict['commerce_product_info']['variations'][0]['shipping']
                product.description = product_dict['description']
                product.status = Product.STATUS_DISABLE
                product.is_new = True

                product.description += '\n'
                for comment in product_dict['top_ratings']:
                    product.description += u'\n{}: "{}"'.format(comment['user']['name'], comment['comment'])

                try:
                    # Wide UCS-4 build
                    myre = re.compile(u'['
                        u'\U0001F300-\U0001F64F'
                        u'\U0001F680-\U0001F6FF'
                        u'\u2600-\u26FF\u2700-\u27BF]+', 
                        re.UNICODE)
                except re.error:
                    # Narrow UCS-2 build
                    myre = re.compile(u'('
                        u'\ud83c[\udf00-\udfff]|'
                        u'\ud83d[\udc00-\ude4f\ude80-\udeff]|'
                        u'[\u2600-\u26FF\u2700-\u27BF])+', 
                        re.UNICODE)

                product.description = myre.sub('', product.description).encode('utf8')
                product.title = myre.sub('', product.title).encode('utf8')

                product.save()

                index = 0
                image_urls = [product_dict['contest_page_picture']]
                image_urls += product_dict['extra_photo_urls'].values()
                for image_url in image_urls:
                    image_url = image_url.replace('-small.', '-original.')
                    _file = StringIO.StringIO(urlopen(image_url).read())
                    img = Image.open(_file)
                    img2 = ImageOps.fit(img, (500,500))
                    
                    tempfile_io = StringIO.StringIO()
                    img2.save(tempfile_io, format='JPEG')
        
                    image_name = '{}-{}-{}.jpg'.format(slugify(product.title), product.id, index)
                    image_file = InMemoryUploadedFile(tempfile_io, None, image_name, 'image/jpeg', \
                            tempfile_io.len, None)

                    photo = ProductPhoto(product=product)
                    photo.image.save(image_name, image_file)
                    photo.save()
                    index += 1

                return product
        return None

    def draw_winners(self, by_friends_count=False, by_most_topups=False):
        bets = self.bets.all()
        win1 = None
        win2 = None
        win3 = None

        if self.drawing_method == Product.DRAWING_METHOD_FB_FRIENDS:
            bets = bets.order_by('-user__friends_count')
        elif self.drawing_method == Product.DRAWING_METHOD_MOST_TOPUP:
            bets = bets.order_by('-user__aggregated_topups')
        elif self.drawing_method == Product.DRAWING_METHOD_CHEAT:
            if not self.win_number:
                raise Exception(_('In order to use cheat mode, win number must be already specificed'))
            bets = bets.annotate(cheat=Case(
                        When(number=self.win_number, then=1), 
                        default=Value(0),
                        output_field=IntegerField()
                    )).order_by('-cheat')            
            # win1 = bets.annotate(cheat=Case(
            #             When(number=self.win_number, then=1), 
            #             default=Value(0),
            #             output_field=IntegerField()
            #         )).order_by('-cheat')
            # win2 = bets.annotate(cheat=Case(
            #             When(number=self.win_second_number, then=1), 
            #             default=Value(0),
            #             output_field=IntegerField()
            #         )).order_by('-cheat')
            # win3 = bets.annotate(cheat=Case(
            #             When(number=self.win_third_number, then=1), 
            #             default=Value(0),
            #             output_field=IntegerField()
            #         )).order_by('-cheat')
        else:
            bets = list(bets)
            random.shuffle(bets)

        if len(bets) == 0:
            return None

        bet = bets[0]
        bet1 = bets[1]
        bet2 = bets[2]

        # if win1:
        #     bet = win1[0]
        # if win2:
        #     bet1 = win2[0]
        # if win3:
        #     bet2 = win3[0]

        self.winner = bet.user

        #Update 1507
        self.winner.enter_his_address_after_8h_48h=0

        self.win_number = bet.number
        self.win_second = bet1.user
        self.win_second_number = bet1.number
        self.win_third = bet2.user
        self.win_third_number = bet2.number
        self.end_date = timezone.now()
        self.latest_chat_date = self.end_date
        self.save()
        
        productwinner = WinnerProduct()
        productwinner.product = self.id
        productwinner.win1 = self.winner.id
        productwinner.win2 = self.win_second.id
        productwinner.win3 = self.win_third.id
        productwinner.save()
        # return 0
        # For creator
        notify.send(self.winner, recipient=self.creator,
                    verb=_('has won your product'), target=self)
        tasks.send_pushnotifs([self.creator.push_channel], {
            'body': u'{} has won your product'.format(self.winner.get_full_name()),
            'product_id': self.id,
            'winner_id': self.winner_id,
            'type': 'BET_SOLD',
            'sound': "default",
        })
        self.creator.append_notification(self.creator.chat_notification_key, self.id)

        # For winner
        notify.send(self.winner, recipient=self.winner,
                    verb=_('has won the product'), target=self)
        tasks.send_pushnotifs([self.winner.push_channel], {
            'body': u'You have won the product "{}"'.format(self.title),
            'product_id': self.id,
            'winner_id': self.winner_id,
            'type': 'BET_WON',
            'prize': 'FIRST',
            'sound': "default",
        })
        self.winner.append_notification(self.winner.activity_notification_key, self.id)
        self.winner.append_notification(self.winner.chat_notification_key, self.id)
        
        # win_second
        notify.send(self.win_second, recipient=self.win_second,
                    verb=_('has won second prize'), target=self)
        tasks.send_pushnotifs([self.win_second.push_channel], {
            'body': u'You won the 2nd prize, collect your cash.',
            'product_id': self.id,
            'winner_id': self.win_second_id,
            'type': 'BET_WON',
            'prize': 'SECOND',
            'sound': "default",
        })
        self.win_second.append_notification(self.win_second.activity_notification_key, self.id)
        self.win_second.append_notification(self.win_second.chat_notification_key, self.id)
        
        # win_third
        notify.send(self.win_third, recipient=self.win_third,
                    verb=_('has won third prize'), target=self)
        tasks.send_pushnotifs([self.win_third.push_channel], {
            'body': u'You won the 3rd prize, collect your cash.',
            'product_id': self.id,
            'winner_id': self.win_third_id,
            'type': 'BET_WON',
            'prize': 'THIRD',
            'sound': "default",
        })
        self.win_third.append_notification(self.win_third.activity_notification_key, self.id)
        self.win_third.append_notification(self.win_third.chat_notification_key, self.id)

        channels = set()
        for b in bets:
            # Check winner
            if (b.user == self.winner) or (b.user == self.win_second) or (b.user == self.win_third):
                continue
            
            notify.send(b.user, recipient=b.user,
                    verb=_('Got result for the product'), target=self)
            channels.add(b.user.push_channel)
            b.user.append_notification(b.user.activity_notification_key, self.id)

        if channels:
            tasks.send_pushnotifs(list(channels), {
                'body': u'Winner for the product {} is available'.format(self.title),
                'product_id': self.id,
                'winner_id': self.winner_id,
                'type': 'BET_FAIL',
                'sound': "default",
            })

        # For sent email
        subject = 'OneDollar - Shipping details of your product'
        html_content = render_to_string('email/won.html', {
            'name':self.winner.first_name, 'product_title': self.title, 'win_number': self.win_number})
        tasks.send_email(subject, html_content, [self.winner.email], from_email='aftersales@onedollarapp.biz')

        subject = 'OneDollar - You sold one of your product : ' + self.title
        html_content = render_to_string('email/sold.html', {
            'name':self.creator.first_name, 'product_title': self.title, 'winner': self.winner, 
            'sold_tickets': self.sold_tickets, 'win_number': self.win_number})
        tasks.send_email(subject, html_content, [self.creator.email])

        if config.AUTO_SHARE_TO_FB_FANPAGE:
            self.share_to_facebook(settings.FB_FANPAGE_ACCESS_TOKEN)

        if self.product_quantity > 1:
            product = copy.copy(self)
            product.id = None
            product.creation_date = product.end_date + dt.timedelta(minutes=product.waiting_time)
            product.end_date = None
            product.winner = None
            product.win_number = None            
            product.win_second = None
            product.win_second_number = None            
            product.win_third = None
            product.win_third_number = None
            product.status = Product.STATUS_ENABLE
            product.sold_tickets = 0
            product.payout_date = None
            product.latest_chat_date = None
            product.delivery_status = Product.DELIVERY_STATUS_NEW
            product.ordering_date = None
            product.ordering_tracking = None
            product.from_shop = None
            product.should_display_seller_popup = 1
            product.should_display_winner_popup = 1
            product.product_quantity -= 1
            product.iteration += 1
            product.save()

            for country in self.country.all():
                product.country.add(country)

            for _photo in self.photos.all():
                photo = copy.copy(_photo)
                photo.id = None
                photo.save()
                product.photos.add(photo)

            product.generate_tickets(force_generate=True)

        return bet
Product._meta.get_field('creator').editable = True


    # truong.append_notification(truong.activity_notification_key, 'self.id')
    # truong.append_notification(truong.chat_notification_key, 'self.id')
        
class SoldProductManager(models.Manager):
    def get_queryset(self):
        return super(SoldProductManager, self).get_queryset().exclude(
                    Q(win_number=None) | 
                    Q(winner=None) | 
                    Q(end_date__gt=dt.datetime.now())
                ).annotate(_days_left_to_ship=RawSQL("GREATEST(0, timestampdiff(DAY, now(), DATE_ADD(end_date, INTERVAL 30 day)))", set()))


class SoldProduct(Product):
    class Meta:
        proxy = True
    objects = SoldProductManager()

    @staticmethod
    def get_pending_products():
        # return SoldProduct.objects.filter(status=Product.DELIVERY_STATUS_PENDING)
        return SoldProduct.objects.filter(delivery_status=SoldProduct.DELIVERY_STATUS_PENDING)

    @property
    def days_left_to_ship(self):
        if hasattr(self, '_days_left_to_ship'):
            return self._days_left_to_ship
        else:
            if self.end_date:
                return max((self.end_date+dt.timedelta(days=30)-timezone.now()).days, 0)
        return None


class ProductPhoto(models.Model):
    image = models.ImageField(_('Picture shall be squared, max 640*640, 500k'), upload_to='photos')
    product = models.ForeignKey(Product, related_name='photos')


class ProductReportingType(models.Model):
    STATUS_ENABLE = 1
    STATUS_DISABLE = 0
    STATUSES = (
        (STATUS_ENABLE, _('Enabled')),
        (STATUS_DISABLE, _('Disabled')),
    )

    name = models.CharField(max_length=100)
    status =  models.SmallIntegerField(choices=STATUSES)

    def __unicode__(self):
        return self.name


class ProductReporting(models.Model):
    product = models.ForeignKey(Product)
    report_type = models.ForeignKey(ProductReportingType)
    creator = models.ForeignKey(OneDollarUser)


class UserReportingType(models.Model):
    STATUS_ENABLE = 1
    STATUS_DISABLE = 0
    STATUSES = (
        (STATUS_ENABLE, _('Enabled')),
        (STATUS_DISABLE, _('Disabled')),
    )

    name = models.CharField(max_length=100)
    status =  models.SmallIntegerField(choices=STATUSES)

    def __unicode__(self):
        return self.name


class UserReporting(models.Model):
    user = models.ForeignKey(OneDollarUser, related_name='reportings_user')
    report_type = models.ForeignKey(UserReportingType)
    creator = models.ForeignKey(OneDollarUser)


class Bet(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    product = models.ForeignKey(Product, related_name='bets')
    number = models.IntegerField()
    creation_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product', 'number')

    @property
    def number_of_friends(self):
        return self.user.friends_count

    @property
    def topups(self):
        return self.user.aggregated_topups


class Transaction(models.Model):
    TYPE_TOPUP = 1
    TYPE_BUY_TICKET = 2
    TYPE_REWARD = 3
    TYPE_REWARD_LIKE = 4
    TYPE_REWARD_RATE = 5
    TYPE_PAY_TO_MERCHANT = 6
    TYPES = (
        (TYPE_TOPUP, _('Top Up')),
        (TYPE_BUY_TICKET, _('Buy Ticket')),
        (TYPE_REWARD, _('Reward')),
        (TYPE_REWARD_LIKE, _('Reward Like')),
        (TYPE_REWARD_RATE, _('Reward Share')),
        (TYPE_PAY_TO_MERCHANT, _('Pay to merchant')),
    )

    CHANNEL_PAYPAL = 1
    CHANNEL_STRIPE = 2
    CHANNELS = (
        (CHANNEL_PAYPAL, _('PayPal')),
        (CHANNEL_STRIPE, _('Stripe')),
    )

    user = models.ForeignKey(OneDollarUser)
    transaction_type = models.SmallIntegerField(choices=TYPES)
    bet = models.ForeignKey(Bet, null=True, blank=True)
    paypal_id = models.CharField(max_length=50, null=True, blank=True)
    amount = models.FloatField()
    money = models.FloatField(null=True, blank=True)
    creation_date = models.DateTimeField(auto_now=True)
    use_free_credit = models.BooleanField(default=True)
    channel = models.SmallIntegerField(choices=CHANNELS, null=True, blank=True)
    transaction_id = models.CharField(max_length=50, null=True, blank=True)
    payer_firstname = models.CharField(max_length=50, null=True, blank=True)
    payer_lastname = models.CharField(max_length=50, null=True, blank=True)
    payer_email = models.CharField(max_length=100, null=True, blank=True)

    @staticmethod
    def get_sum_topup_by_channel():
        return Transaction.objects.filter(transaction_type=Transaction.TYPE_TOPUP).aggregate( \
                PayPal=Sum(Case(When(channel=Transaction.CHANNEL_PAYPAL, then='money'))), \
                Stripe=Sum(Case(When(channel=Transaction.CHANNEL_STRIPE, then='money'))))

    @staticmethod
    def get_stripe_error_stats():
        r = get_redis_connection()
        stats = r.hgetall(settings.REDISKEYS_STRIPE_ERR)
        ret = {}

        for k, v in stats.items():
            if k.endswith('.##total'):
                continue
            key = k[:k.rfind('.##')]
            ret[key] = '${} / {} times'.format(stats[key+'.##total'], v)

        return ret

    @staticmethod
    def get_topups_in_90_days():
        date_90_days_ago = dt.datetime.now() - dt.timedelta(days=90)
        return Transaction.objects.filter(transaction_type=Transaction.TYPE_TOPUP, creation_date__gte=date_90_days_ago).order_by('-creation_date')

    @staticmethod
    def get_sum_all_topups():
        ret = Transaction.objects.filter(transaction_type=Transaction.TYPE_TOPUP).aggregate(sum_topups=Sum('money'))
        if ret and ret.has_key('sum_topups') and ret['sum_topups'] > 0:
            return ret['sum_topups']
        return 0

@receiver(post_delete, sender=Transaction)
def update_transaction_on_delete(sender, instance=None, **kwargs):
    if instance.use_free_credit:
        instance.user.free_credits = F('free_credits') - instance.amount
    else:
        instance.user.credits = F('credits') - instance.amount
    instance.user.save()

    if hasattr(instance, 'bet') and instance.bet:
        instance.bet.delete()

@receiver(post_save, sender=Transaction)
def update_transaction_on_create(sender, instance=None, created=False, **kwargs):
    if created:
        if instance.transaction_type == Transaction.TYPE_BUY_TICKET and hasattr(instance, 'bet') \
                and hasattr(instance.bet, 'product'):
            if instance.user.free_credits > 0 and instance.bet.product.is_sponsored:
                instance.user.free_credits = F('free_credits') + instance.amount
            elif instance.user.credits > 0:
                instance.user.credits = F('credits') + instance.amount
                instance.use_free_credit = False
                instance.save()
            else:
                raise Exception('NO_CREDITS_LEFT')
        elif instance.transaction_type == Transaction.TYPE_TOPUP:
            instance.user.credits = F('credits') + instance.amount
            instance.use_free_credit = False
            instance.save()

            instance.user.aggregated_topups = F('aggregated_topups') + instance.money
            instance.user.is_recharged = True

            if instance.user.referrer_id and instance.amount >= config.REFERRAL_TOPUP_REQUIRE:
                ret = OneDollarUser.objects.filter(id=instance.user.referrer_id, receive_bonus=False) \
                        .update(credits=F('credits')+config.REFERRAL_TOPUP_REWARD, receive_bonus=True)
                if ret:
                    tasks.send_pushnotifs([instance.user.referrer.push_channel], {
                        'body': u'Your account has just been updated',
                        'user_id': instance.user.referrer.id,
                        'type': 'PROFILE_UPDATED',
                    })

            tasks.send_pushnotifs([instance.user.push_channel], {
                'body': u'Your account has just been updated',
                'user_id': instance.user.id,
                'type': 'PROFILE_UPDATED',
            })
        elif instance.transaction_type == Transaction.TYPE_REWARD or \
                instance.transaction_type == Transaction.TYPE_REWARD_RATE or \
                instance.transaction_type == Transaction.TYPE_REWARD_LIKE:
            instance.user.free_credits = F('free_credits') + instance.amount
            instance.use_free_credit = True
            instance.save()

        instance.user.save()


class Country(models.Model):
    class Meta:
        verbose_name_plural = _('Countries')

    STATUS_DISABLE = 0
    STATUS_ENABLE = 10
    STATUSES = (
        (STATUS_DISABLE, _("Disable")),
        (STATUS_ENABLE, _("Enable")),
    )

    name = models.CharField(max_length=100)
    currency_code = models.CharField(max_length=10)
    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True)
    status = models.SmallIntegerField(choices=STATUSES, default=STATUS_DISABLE)

    def __unicode__(self):
        return '{} ({})'.format(self.name, self.currency_code)


class TopupPackage(models.Model):
    TYPE_PAYPAL = 1
    TYPE_STRIPE = 2
    TYPES = (
        (TYPE_PAYPAL, _("PayPal")),
        (TYPE_STRIPE, _("Stripe")),
    )

    type = models.SmallIntegerField(choices=TYPES, default=TYPE_PAYPAL, editable=False)
    name = models.CharField(max_length=100)
    topup_value = models.IntegerField(_('topup value'), default=0)
    credits = models.IntegerField(_('credits'), default=0)

    class Meta:
        ordering = ['type', 'topup_value']

class ProductCount(models.Model):
    product = models.ForeignKey(Product)
    count = models.IntegerField(default=0)

class UserLucky(models.Model):
    user = models.ForeignKey(OneDollarUser)
    count = models.IntegerField(default=0)
    is_have_chance = models.IntegerField(default=0)

class UserCatSpin(models.Model):
    FULL = 1
    FREE = 0
    RUNNING = 2
    SPIN = 3
    TYPES = (
        (FULL, _("Full")),
        (FREE, _("Free")),
        (RUNNING, _("Running")),
        (SPIN, _("Spin")),
    )
    user = models.ForeignKey(OneDollarUser)
    daily_1 = models.DateTimeField(auto_now_add=True)
    daily_2 = models.DateTimeField(auto_now_add=True)

    slot_1 = models.SmallIntegerField(choices=TYPES, default=FREE)
    time_1 = models.DateTimeField(auto_now_add=True)    

    slot_2 = models.SmallIntegerField(choices=TYPES, default=FREE)
    time_2 = models.DateTimeField(auto_now_add=True)

    slot_3 = models.SmallIntegerField(choices=TYPES, default=FREE)
    time_3 = models.DateTimeField(auto_now_add=True)

    slot_4 = models.SmallIntegerField(choices=TYPES, default=FREE)
    time_4 = models.DateTimeField(auto_now_add=True)

    coins = models.IntegerField(default=0)
    level = models.IntegerField(default=0)

    discount = models.FloatField(null=True, default=0)

def before_the_draw_30_min():
    temp = dt.datetime.now()+dt.timedelta(minutes=30)
    products = Product.objects.exclude(win_number__isnull=False).filter(no_of_days__isnull=False,end_date__lt=temp,end_date__gt=dt.datetime.now())
    channels = set()
    users = OneDollarUser.objects.all()
    for user in users:
        channels.add(user.pk)
        # notify.send(user, recipient=user,
        #         verb=_('30 min left before the draw'), target=user)
    for product in products:
        tasks.send_pushnotifs(list(channels), {
            'body': u'30 min left before the draw, last chance to bet again',
        #     'product_id': 'day la product_id',
        #     'winner_id': 'winner_id',
        #     'type': 'BET_WON',
        #     'prize': 'THIRD',
        })

def enter_his_address_after_8h():
    temp = dt.datetime.now()-dt.timedelta(days=30)
    products = Product.objects.filter(win_number__isnull=False,end_date__gt=temp,end_date__lt=dt.datetime.now())
    channels = set()
    for product in products:
        if product.winner.street1 and product.winner.postal_code and product.winner.province and product.winner.city:
            continue      
        if product.winner.enter_his_address_after_8h_48h<2:
            hour = [8,48]
            nexttime = product.end_date+dt.timedelta(hours=hour[product.winner.enter_his_address_after_8h_48h])
            if dt.datetime.now(timezone.utc)>nexttime:
                channels.add(product.winner.pk)
                product.winner.enter_his_address_after_8h_48h=product.winner.enter_his_address_after_8h_48h+1
                product.winner.save()

    tasks.send_pushnotifs(list(channels), {
        'body': u'CLAIM your price before it expires',
    })

def collect_your_cash_4h():
    products =  WinnerProduct.objects.all()
    channels2 = set()
    channels3 = set()
    for product in products:
        if not product.win2==-1:
            user = OneDollarUser.objects.get(id=product.win2)
            if user.collect_your_cash_4h_24h<2:
                hour = [4,24]
                nexttime = Product.objects.get(id=product.product).end_date+dt.timedelta(hours=hour[user.collect_your_cash_4h_24h])
                if dt.datetime.now(timezone.utc)>nexttime:
                    channels2.add(product.win2)
                    user.collect_your_cash_4h_24h=user.collect_your_cash_4h_24h+1
                    user.save()
            continue

        if not product.win3==-1:
            user = OneDollarUser.objects.get(id=product.win3)
            if user.collect_your_cash_4h_24h<2:
                hour = [4,24]
                print Product.objects.get(id=product.product).end_date
                nexttime = Product.objects.get(id=product.product).end_date+dt.timedelta(hours=hour[user.collect_your_cash_4h_24h])
                if dt.datetime.now(timezone.utc)>nexttime:
                    channels3.add(product.win3)
                    user.collect_your_cash_4h_24h=user.collect_your_cash_4h_24h+1
                    user.save()

    tasks.send_pushnotifs(list(channels2), {
        'body': u'You won the 2nd prize, collect your cash',
        'type': 'BET_WON',
        'prize': 'SECOND',
    })

    tasks.send_pushnotifs(list(channels3), {
        'body': u'You won the 3rd prize, collect your cash',
        'type': 'BET_WON',
        'prize': 'THIRD',
    })

def second_chance_4h():
    channels = set()
    users = UserLucky.objects.filter(is_have_chance=1)
    for user in users:
        if user.user.second_chance_4h_48h<2:
            hour = [4,48]
            nexttime = user.user.last_login+dt.timedelta(hours=hour[user.user.second_chance_4h_48h])
            if dt.datetime.now(timezone.utc)>nexttime:
                channels.add(user.user.id)
                user.user.second_chance_4h_48h = user.user.second_chance_4h_48h+1
                user.user.save()

    tasks.send_pushnotifs(list(channels), {
        'body': u'Spin your lucky cat and get a second chance to win',
        'type': 'SECOND_CHANCE',
    })

def pns_free_daily_cat():
    temp1 = dt.datetime.now(timezone.utc)
    temp2 = dt.datetime.now(timezone.utc)+dt.timedelta(minutes=1)
    channels = set()
    users = UserCatSpin.objects.all()
    for user in users:
        if (user.daily_1<temp2 and user.daily_1>temp1) or (user.daily_2<temp2 and user.daily_2>temp1):
            channels.add(user.user.id)
    tasks.send_pushnotifs(list(channels), {
        'body': u'Free daily cat is waiting for you, time to spin it',
        'type': 'GAME_CAT',
    })

def pns_spin_cat_uncage():
    temp1 = dt.datetime.now(timezone.utc)
    temp2 = dt.datetime.now(timezone.utc)+dt.timedelta(minutes=1)
    channels = set()
    users = UserCatSpin.objects.all()
    for user in users:
        if (user.time_1<temp2 and user.time_1>temp1 and user.slot_1==2)or(user.time_2<temp2 and user.time_2>temp1 and user.slot_2==2)or(user.time_3<temp2 and user.time_3>temp1 and user.slot_3==2)or(user.time_4<temp2 and user.time_4>temp1 and user.slot_4==2):
            channels.add(user.user.id)

    tasks.send_pushnotifs(list(channels), {
        'body': u'Cat unlocked, time to spin it',
        'type': 'GAME_CAT',
    })

def pns_uncage_cat_remind():
    temp = dt.datetime.now()
    channels = set()
    users = UserCatSpin.objects.filter(Q(slot_1=1) | Q(slot_2=1) | Q(slot_3=1) | Q(slot_4=1))
    for user in users:
        channels.add(user.user.id)
        # notify.send(user.user, recipient=user.user,
        #     verb=_('Uncage your lucky cat'), target=user.user)
    tasks.send_pushnotifs(list(channels), {
        'body': u'Unlock your lucky cat',
        'type': 'GAME_CAT',
    })    

def pns_uncage_cat_remind_after_1day():
    temp = dt.datetime.now() - dt.timedelta(days=1)
    channels = set()
    users = UserCatSpin.objects.filter(Q(time_1__lt=temp, slot_1=1) | Q(time_2__lt=temp, slot_2=1) | Q(time_3__lt=temp, slot_3=1) | Q(time_4__lt=temp, slot_4=1))
    for user in users:
        channels.add(user.user.id)
        # notify.send(user.user, recipient=user.user,
        #     verb=_('Oops! You forgot to uncage a cat'), target=user.user)
    tasks.send_pushnotifs(list(channels), {
        'body': u'Oops! You forgot to uncage a cat',
        'type': 'GAME_CAT',
    })    