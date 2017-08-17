# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('merchants', '0003_auto_20170717_0913'),
    ]

    operations = [
        migrations.AlterField(
            model_name='store',
            name='provider_payment',
            field=models.SmallIntegerField(blank=True, null=True, choices=[(1, 'PayPal'), (2, 'Payoneer')]),
        ),
    ]
