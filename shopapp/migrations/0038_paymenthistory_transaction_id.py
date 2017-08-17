# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0037_order_variation'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymenthistory',
            name='transaction_id',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
    ]
