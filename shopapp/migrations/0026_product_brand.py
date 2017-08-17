# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0011_auto_20170728_1219'),
        ('shopapp', '0025_auto_20170728_1219'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='brand',
            field=models.ForeignKey(blank=True, to='onedollar.Brand', null=True),
        ),
    ]
