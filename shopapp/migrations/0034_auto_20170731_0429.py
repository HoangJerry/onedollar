# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0033_auto_20170731_0428'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymenthistory',
            name='creation_date',
            field=models.DateField(null=True, blank=True),
        ),
    ]
