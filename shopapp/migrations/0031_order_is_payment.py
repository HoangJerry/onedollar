# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0030_auto_20170729_0126'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='is_payment',
            field=models.BooleanField(default=False),
        ),
    ]
