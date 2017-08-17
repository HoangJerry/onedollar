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
from unify_django import api_utils


class StoreSerializer(serializers.ModelSerializer):
    provider_payment = serializers.SerializerMethodField('_provider_payment')
    class Meta:
        model = Store
    def _provider_payment(self, obj):
        return obj.get_provider_payment_display()
        
class EmailFagsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailFags