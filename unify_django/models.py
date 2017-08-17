from urllib2 import urlopen
from django.core.files.base import ContentFile

from django.db.models import options
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import BaseUserManager, UserManager, \
    AbstractBaseUser, PermissionsMixin
from django.contrib.auth import get_user_model
from django.utils.text import slugify

import facebook


def refresh_model(obj):
    """ Reload an object from the database """
    return obj.__class__._default_manager.get(pk=obj.pk)


class BaseModelMixinManager(models.Manager):
    def get_queryset(self):
        return super(BaseModelMixinManager, self).get_queryset().all()


class BaseModelMixin(models.Model):
    """
    All models will have these fields for keep track
    of who and when create / update
    """

    STATUS_DISABLE = 0
    STATUS_ENABLE = 10
    STATUSES = (
        (STATUS_DISABLE, _("Disable")),
        (STATUS_ENABLE, _("Enable")),
    )

    creation_date = models.DateTimeField(auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, editable=False)
    status = models.SmallIntegerField(choices=STATUSES, default=STATUS_DISABLE)
    objects = models.Manager()
    showable = BaseModelMixinManager()

    class Meta:
        abstract = True


options.DEFAULT_NAMES = options.DEFAULT_NAMES + ('unf_icon_size', 'unf_image_field')


class ThumbInListMixin(models.Model):
    class Meta:
        abstract = True
        unf_icon_size = (30, 30)
        unf_image_field = 'image'

    def adminlist_thumbnail(self):
        image_field = getattr(self, self._meta.unf_image_field, None)

        if not image_field:
            return '<i>NA</i>'

        width = self._meta.unf_icon_size[0] or 'auto'
        height = self._meta.unf_icon_size[1] or 'auto'
        return u'<img src="%s" width="%s" height="%s" />' % \
               (image_field.url, width, height)

    adminlist_thumbnail.short_description = _('Thumbnail')
    adminlist_thumbnail.allow_tags = True


class UnifyBaseUserManager(BaseUserManager):
    def create_user(self, username="", email=None, password=None, commit=True, **extra_fields):
        now = timezone.now()
        if not email:
            raise ValueError('The given email must be set')
        email = UserManager.normalize_email(email)
        username = username if username else email
        user = self.model(username=username, email=email,
                          is_staff=False, is_active=True, is_superuser=False,
                          last_login=now, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        if commit:
            user.save(using=self._db)

        return user

    def get_or_create_user_from_googleplus(self, gp_token):
        UserModel = get_user_model()
        ret = False
        try:
            r = requests.get('https://www.googleapis.com/plus/v1/people/me?access_token=' + gp_token)

            if r.status_code == 200:
                user = r.json()
                print user

                email = ''
                for data in user.get('emails'):
                    if data.get('type') == 'account':
                        email = data.get('value')
                        break

                username = email
                gp_uid = user.get('id')

                name = user.get('name', {})
                first_name = name.get('givenName', '')
                last_name = name.get('familyName', '')
                gender = (user.get('gender', '') == 'male') \
                         and UserModel.CONST_GENDER_MALE or UserModel.CONST_GENDER_FEMALE
                relationship_status = ''
                about = ''
                dob = user.get('birthday', '')

                image = user.get('image', {})
                avatar_url = image.get('url')

                if avatar_url:
                    avatar_url = avatar_url.replace('sz=50', 'sz=500')

                try:
                    ret = self.get(gp_uid=gp_uid)
                except UserModel.DoesNotExist:
                    try:
                        ret = self.get(email=email)
                    except UserModel.DoesNotExist:
                        ret = self.create_user(username=username, email=email, commit=False)

                ret.gp_uid = gp_uid
                ret.gp_access_token = gp_token

                ret = self.update_user_data(ret, username, email, first_name, last_name,
                                            gender, relationship_status, about, dob, avatar_url)
        except Exception as e:
            print ">>> get_or_create_user_from_googleplus ::", e
            pass

        return ret

    def get_or_create_user_from_facebook(self, fb_token, default_username=None, default_email=None, should_create=True):
        UserModel = get_user_model()
        ret = False
        try:
            graph = facebook.GraphAPI(fb_token)
            user = graph.get_object("me")

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

            ret.fb_uid = fb_uid
            ret.fb_access_token = fb_token

            ret = self.update_user_data(ret, username, email, first_name, last_name,
                                        gender, relationship_status, about, dob, avatar_url)
        except Exception as e:
            print ">>> get_or_create_user_from_facebook ::", e
            pass

        return ret

    def update_user_data(self, user, username, email, first_name,
                         last_name, gender, relationship_status, about, dob, avatar_url):
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

        user.save()
        return user

    def create_superuser(self, username, email, password, **extra_fields):
        u = self.create_user(username, email, password, **extra_fields)
        u.is_staff = True
        u.is_active = True
        u.is_superuser = True
        u.save(using=self._db)
        return u


class UnifyBaseUser(AbstractBaseUser, PermissionsMixin):
    class Meta:
        verbose_name = _("User")
        abstract = True

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    CONST_GENDER_FEMALE = 0
    CONST_GENDER_MALE = 1
    CONST_GENDER_BOTH = 2
    CONST_GENDERS = (
        (CONST_GENDER_FEMALE, _('Female')),
        (CONST_GENDER_MALE, _('Male')),
        (CONST_GENDER_BOTH, _('Both')),
    )

    CONST_STATUS_ENABLED = 0
    CONST_STATUS_BLOCKED = 10
    CONST_STATUS_DELETED = 20
    CONST_STATUSES = (
        (CONST_STATUS_ENABLED, _('Enabled')),
        (CONST_STATUS_BLOCKED, _('Blocked')),
        (CONST_STATUS_DELETED, _('Deleted')),
    )

    email = models.CharField(max_length=254, unique=True)
    username = models.CharField(max_length=40, unique=True, db_index=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.PositiveSmallIntegerField(_('gender'), choices=CONST_GENDERS, \
                                              default=CONST_GENDER_MALE)
    fb_access_token = models.TextField(null=True, blank=True)
    fb_uid = models.CharField(max_length=50, unique=True, null=True, blank=True)
    gp_uid = models.CharField(max_length=50, unique=True, null=True, blank=True)
    gp_access_token = models.TextField(null=True, blank=True)
    parse_id = models.CharField(max_length=20, null=True, blank=True)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    is_staff = models.BooleanField(_('staff status'), default=False,
                                   help_text=_('Designates whether the user can log into this admin '
                                               'site.'))
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_('Designates whether this user should be treated as '
                                                'active. Unselect this instead of deleting accounts.'))
    status = models.PositiveSmallIntegerField(_('status'), choices=CONST_STATUSES,
                                              default=CONST_STATUS_ENABLED)

    about = models.TextField(null=True, blank=True)
    relationship_status = models.CharField(null=True, blank=True, max_length=30)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    avatar = models.ImageField(upload_to='avatars', null=True, blank=True)

    objects = UnifyBaseUserManager()

    @property
    def can_login(self):
        return self.is_active and self.status == self.CONST_STATUS_ENABLED

    @property
    def notifications_count(self):
        return self.notifs_to.filter(is_read=False).count()

    @property
    def token(self):
        return self.auth_token.key

    def get_gender(self):
        return dict(self.CONST_GENDERS).get(self.gender)

    def get_short_name(self):
        return self.first_name

    def get_full_name(self):
        return '%s %s' % (self.first_name, self.last_name)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.username:
            self.username = self.email
        super(UnifyBaseUser, self).save(force_insert, force_update, using, update_fields)

    def update_current_location(self, lat, lng):
        self.latitude = lat
        self.longitude = lng
        self.save()
