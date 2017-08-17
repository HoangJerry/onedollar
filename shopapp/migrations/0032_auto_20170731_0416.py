# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0031_order_is_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymenthistory',
            name='creation_date',
            field=models.DateField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='paymenthistory',
            name='total_amount',
            field=models.FloatField(default=0, null=True, blank=True),
        ),
    ]
