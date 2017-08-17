from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_save, post_delete
from django.db.models import F, Sum, Count

from multiselectfield import MultiSelectField, MultiSelectFormField
import onedollar.models as onedollar_models

# Create your models here.
class Store(models.Model):
    CHANNEL_PAYPAL = 1
    CHANNEL_PAYONEER = 2
    CHANNELS = (
        (CHANNEL_PAYPAL, _('PayPal')),
        (CHANNEL_PAYONEER, _('Payoneer')),
    )

    CONST_STATUS_ENABLED = 0
    CONST_STATUS_BLOCKED = 10
    CONST_STATUS_DELETED = 20
    CONST_STATUS_NOT_FINALIZED = 30
    CONST_STATUS_PENDING = 40
    CONST_STATUSES = (
        (CONST_STATUS_ENABLED, _('Enabled')),
        (CONST_STATUS_BLOCKED, _('Blocked')),
        (CONST_STATUS_DELETED, _('Deleted')),
        (CONST_STATUS_NOT_FINALIZED, _('Not finalized')),
        (CONST_STATUS_PENDING, _('Pending for approvel')),
    )

    status = models.PositiveSmallIntegerField(choices=CONST_STATUSES,default=CONST_STATUS_NOT_FINALIZED)


    user = models.ForeignKey(onedollar_models.OneDollarUser)
    store_platform = models.CharField(max_length=50, null=True, blank=True)
    url_store_platform = models.CharField(max_length=200, null=True, blank=True)
    revenue_last_year = models.FloatField(null=True, blank=True)
    warehouse_located = models.CharField(max_length=50, null=True, blank=True)
    warehouse_street = models.CharField(max_length=200, null=True, blank=True)
    product_categories = models.CharField(max_length=200, null=True, blank=True)
    provider_payment = models.SmallIntegerField(choices=CHANNELS, null=True, blank=True)
    email_payment = models.CharField(max_length=200, null=True, blank=True)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        userstore = onedollar_models.OneDollarUser.objects.get(pk=self.user.id)
        userstore.is_staff=True
        userstore.status = self.status
        if self.status==Store.CONST_STATUS_BLOCKED:
            userstore.is_staff=False
        userstore.save()
        if self.status==Store.CONST_STATUS_DELETED:
            super(Store, self).delete()
            userstore.delete()
        else: 
            super(Store, self).save(force_insert, force_update, using, update_fields)

class  EmailFags(models.Model):
    user = models.ForeignKey(onedollar_models.OneDollarUser)
    receive_an_order  = models.BooleanField(default=True)
    approve_a_new_product = models.BooleanField(default=True)
    received_a_payment_product = models.BooleanField(default=True)
    do_not_send_me_any_of_these_emails = models.BooleanField(default=False)
