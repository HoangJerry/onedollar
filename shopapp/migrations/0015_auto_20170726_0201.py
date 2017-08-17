# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0014_auto_20170720_0211'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='channel',
            field=models.SmallIntegerField(blank=True, null=True, choices=[(1, 'PayPal'), (2, 'Stripe'), (3, 'Google Pay')]),
        ),
    ]
