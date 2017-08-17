# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0010_brand'),
        ('shopapp', '0023_paymenthistory_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='brand',
            field=models.ForeignKey(related_name='shopproductbrand', blank=True, to='onedollar.Brand', null=True),
        ),
    ]
