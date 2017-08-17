# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0016_auto_20170726_0741'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='delivery_status',
            field=models.SmallIntegerField(default=0, choices=[(0, 'New'), (10, 'Processing'), (20, 'Shipped'), (30, 'Arrived'), (40, 'Refunded by merchants'), (60, 'Refunded by admin'), (50, 'Blocked or Fraud')]),
        ),
        migrations.AlterField(
            model_name='order',
            name='transaction_code',
            field=models.CharField(max_length=300, null=True, blank=True),
        ),
    ]
