# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0010_auto_20170715_0239'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='delivery_status',
            field=models.SmallIntegerField(default=0, choices=[(0, 'New'), (10, 'Processing'), (20, 'Shiped'), (30, 'Arrived'), (40, 'Refunded'), (50, 'Blocked or Fraud')]),
        ),
    ]
