# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0011_auto_20170718_0113'),
    ]

    operations = [
        migrations.AddField(
            model_name='unique',
            name='buying_price',
            field=models.FloatField(default=0, blank=True),
        ),
        migrations.AddField(
            model_name='unique',
            name='shipping_cost',
            field=models.FloatField(default=0),
        ),
    ]
