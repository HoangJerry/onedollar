# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0007_auto_20170726_0741'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='transaction_type',
            field=models.SmallIntegerField(choices=[(1, 'Top Up'), (2, 'Buy Ticket'), (3, 'Reward'), (4, 'Reward Like'), (5, 'Reward Share'), (6, 'Pay to merchant')]),
        ),
    ]
