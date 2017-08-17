from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save, post_delete
from django.db.models import F, Sum, Count
import datetime as dt

from multiselectfield import MultiSelectField, MultiSelectFormField
from unify_django.models import BaseModelMixinManager
from unify_django.models import *
from merchants import api as merchants_api


from onedollar.models import CategoryTest, Country, Brand

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

    STATUS_DISABLE = 0
    STATUS_ENABLE = 10
    STATUS_PENDING = 20
    STATUS_APPROVED = 30
    STATUS_REJECT = 40
    STATUSES = (
        (STATUS_DISABLE, _("Disable")),
        (STATUS_ENABLE, _("Enable")),
        (STATUS_PENDING, _("Pending")),
        (STATUS_APPROVED, _("Approved")),
        (STATUS_REJECT, _("Rejected")),
    )

    COLORS = (('White', 'White'),
              ('Green', 'Green'),
              ('Beige', 'Beige'),
              ('Ivory', 'Ivory'),
              ('Black', 'Black'),
              ('Grey', 'Grey'),
              ('Pink', 'Pink'),
              ('NavyBlue', 'Navy Blue'),
              ('Red', 'Red'),
              ('Brown', 'Brown'),
              ('Orange', 'Orange'),
              ('Purple', 'Purple'),
              ('Blue', 'Blue'),
              ('Tan', 'Tan'),
              ('Yellow', 'Yellow'),
              ('Gold', 'Gold'),
              ('Multicolor', 'Multicolor'))

    SIZES = (('XXS', 'XXS'),
             ('XS', 'XS'),
             ('S', 'S'),
             ('M', 'M'),
             ('L', 'L'),
             ('XL', 'XL'),
             ('XXL', 'XXL'),
             ('XXXL', 'XXXL'))

    SHIPPING_TIMES = ((0, '0'),
                     (1, '5 - 10'),
                     (2, '7 - 14'),
                     (3, '10 - 15'),
                     (4, '14 - 21'),
                     (5, '21 - 28'))

    creation_date = models.DateTimeField()
    modification_date = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, editable=False, related_name='shopproduct')
    status = models.SmallIntegerField(choices=STATUSES, default=STATUS_PENDING)

    # update
    product_parent = models.ForeignKey('self',blank=True,null=True)

    country = models.ManyToManyField(Country, related_name='shopproduct')
    unique_id = models.CharField(max_length=200, null=True, blank=True)
    title = models.CharField(_('title'), max_length=200)
    category = models.ForeignKey(CategoryTest, null=True, blank=True, related_name='shopproduct')
    category_child = models.ForeignKey('categories.Category', null=True, blank=True, related_name='shopproduct')
    brand = models.ForeignKey(Brand, null=True, blank=True,related_name='shopproducthehe')
    description = models.TextField(_('description'))
    quantity = models.PositiveIntegerField(null=True, blank=True, help_text=_('Skip this field to make the quantity unlimited'))
    colors = MultiSelectField(choices=COLORS, null=True, blank=True)
    sizes = MultiSelectField(choices=SIZES, null=True, blank=True)
    shipping_time = models.PositiveSmallIntegerField(choices=SHIPPING_TIMES)
    shipping_cost = models.FloatField(default=0)
    retail_price = models.FloatField()
    # reward_tokens = models.PositiveIntegerField(default=0)
    reward_tokens = models.IntegerField(default=0)
    buying_price = models.FloatField()
    tags = models.TextField(null=True, blank=True)
    earning = models.FloatField(null=True, blank=True, editable=False)

    delivery_status = models.SmallIntegerField(choices=DELIVERY_STATUSES, default=DELIVERY_STATUS_NEW)
    ordering_date = models.DateField(null=True, blank=True)
    ordering_tracking = models.CharField(null=True, blank=True, max_length=1000)

    latest_chat_date = models.DateTimeField(_('latest_chat_date'), null=True, blank=True, editable=False)
    should_display_winner_popup = models.BooleanField(default=True)
    should_display_seller_popup = models.BooleanField(default=True)

    orders_count = models.PositiveIntegerField(default=0)

    showable = BaseModelMixinManager()
    objects = models.Manager()
    _default_manager = objects

    def __unicode__(self):
        return self.title

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if Product.objects.filter(id=self.id):
            if not self.status == Product.objects.get(id=self.id).status:
                if self.status==Product.STATUS_APPROVED:
                    merchants_api.SendProductAprrovedEmail(product=self.title,creator=self.creator.id)
        super(Product, self).save(force_insert, force_update, using, update_fields)

    def __init__(self, *args, **kwargs):
        super(Product, self).__init__(*args, **kwargs)
        self.initial_quantity = self.quantity if self.id else 0
       

    @property
    def product_edit_url(self):
        return u'<a href="{}" target="_blank">{}</a>'.format(reverse('admin:onedollar_product_change', args=[self.id]),
                                            self.title)

    @property
    def parents(self):
        temp = self.product_parent
        if temp=='NULL':
            return None
        return temp
    @property
    def pl_value(self):
        return self.retail_price-self.cost

    @property
    def countries(self):
        return '<br />'.join(self.country.all().values_list('name', flat=True))
    
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

Product._meta.get_field('creator').editable = True


class ProductPhoto(models.Model):
    image = models.ImageField(_('Picture shall be squared, max 640*640, 500k'), upload_to='shop-photos')
    product = models.ForeignKey(Product, related_name='photos')


class Unique(models.Model):
    unique_id = models.CharField(max_length=100, null=True, blank=True)
    size = models.CharField(max_length=10, null=True, blank=True)
    color = models.CharField(max_length=10, null=True, blank=True)
    quantity = models.IntegerField(default=0,null=True, blank=True)
    product_sold = models.IntegerField(default=0,null=True, blank=True)
    buying_price = models.FloatField(blank=True,default=0,)
    shipping_cost = models.FloatField(default=0)
    product = models.ForeignKey(Product, related_name='uniques')

class Order(models.Model):
    CHANNEL_PAYPAL = 1
    CHANNEL_STRIPE = 2
    CHANNEL_GOOGLE_PAY = 3
    CHANNELS = (
        (CHANNEL_PAYPAL, _('PayPal')),
        (CHANNEL_STRIPE, _('Stripe')),
        (CHANNEL_GOOGLE_PAY, _('Google Pay')),
    )


    DELIVERY_STATUS_NEW = 0
    DELIVERY_STATUS_PROCESSING = 10
    DELIVERY_STATUS_SHIPPED = 20
    DELIVERY_STATUS_ARRIVED = 30
    DELIVERY_STATUS_NOTSENT = 40
    DELIVERY_STATUS_NOTSENTADMIN = 60
    DELIVERY_STATUS_BLOCKEDORFRAUD= 50
    DELIVERY_STATUSES = (
        (DELIVERY_STATUS_NEW, _("New")),
        (DELIVERY_STATUS_PROCESSING, _("Processing")),
        (DELIVERY_STATUS_SHIPPED, _("Shipped")),
        (DELIVERY_STATUS_ARRIVED, _("Arrived")),
        (DELIVERY_STATUS_NOTSENT, _("Refunded by merchants")),
        (DELIVERY_STATUS_NOTSENTADMIN, _("Refunded by admin")),
        (DELIVERY_STATUS_BLOCKEDORFRAUD, _("Blocked or Fraud")),
    )

    SHIPPING_TIMES = ((0, '0'),
                     (1, '5 - 10'),
                     (2, '7 - 14'),
                     (3, '10 - 15'),
                     (4, '14 - 21'),
                     (5, '21 - 18'))

    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    product = models.ForeignKey(Product, related_name='orders')
    amount = models.FloatField()
    reward_tokens = models.IntegerField()
    channel = models.SmallIntegerField(choices=CHANNELS, null=True, blank=True)
    transaction_code = models.CharField(max_length=300, null=True, blank=True)
    transaction_id = models.CharField(max_length=50, null=True, blank=True)
    payer_firstname = models.CharField(max_length=50, null=True, blank=True)
    payer_lastname = models.CharField(max_length=50, null=True, blank=True)
    payer_email = models.CharField(max_length=100, null=True, blank=True)
    firstname = models.CharField(max_length=50, null=True, blank=True)
    lastname = models.CharField(max_length=50, null=True, blank=True)
    email = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    street1 = models.CharField(max_length=300, null=True, blank=True)
    street2 = models.CharField(max_length=300, null=True, blank=True)
    postal_code = models.CharField(max_length=10, null=True, blank=True)
    province = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    country = models.ForeignKey(Country, null=True, blank=True)
    delivery_status = models.SmallIntegerField(choices=DELIVERY_STATUSES, default=DELIVERY_STATUS_NEW)
    shipping_time = models.PositiveSmallIntegerField(choices=SHIPPING_TIMES, null=True, blank=True)
    tracking_number = models.CharField(max_length=100, null=True, blank=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    note_yourself = models.CharField(max_length=200, null=True, blank=True)
    is_payment_on = models.DateTimeField(null=True, blank=True)
    variation = models.CharField(max_length=200, null=True, blank=True)
    @staticmethod
    def get_sum_all_orders():
        return Order.objects.exclude(delivery_status__in=[40,60]).aggregate(count_orders=Count('id'), sum_orders=Sum('amount'))

@receiver(post_save, sender=Order)
def increase_product_orders_count(sender, instance=None, created=False, **kwargs):
    if created:
        instance.product.orders_count = F('orders_count') + 1
        instance.product.save()


@receiver(post_delete, sender=Order)
def decrease_product_orders_count(sender, instance=None, created=False, **kwargs):
    instance.product.orders_count = F('orders_count') - 1
    instance.product.save()

class CoinCount(models.Model):
    COUNT_COIN_SWAP = 0
    ANOTHER_DEV = 10
    COUNT_COIN_FOR = (
        (COUNT_COIN_SWAP, _("swap")),
        (ANOTHER_DEV, _("another")),
    )
    
    count_for = models.SmallIntegerField(choices=COUNT_COIN_FOR, default=COUNT_COIN_SWAP)
    count = models.IntegerField(default=0)

class PaymentHistory(models.Model):
    STATUS_UPCOMING = 0
    STATUS_PENDING = 10
    STATUS_COMPLETED = 20
    STATUSES = (
        (STATUS_UPCOMING, _("Upcoming")),
        (STATUS_PENDING, _("Pending")),
        (STATUS_COMPLETED, _("Completed")),
    )

    merchant = models.ForeignKey(settings.AUTH_USER_MODEL, editable=False, related_name='merchant')
    payment_history = models.CharField(max_length=100, null=True, blank=True)
    total_amount = models.FloatField(default=0,null=True, blank=True)
    status = models.SmallIntegerField(choices=STATUSES, default=STATUS_UPCOMING)
    payout_item_id = models.CharField(max_length=100, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)

