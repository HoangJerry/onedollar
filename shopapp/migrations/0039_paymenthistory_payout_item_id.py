# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0038_paymenthistory_transaction_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymenthistory',
            name='payout_item_id',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
    ]
