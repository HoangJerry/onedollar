# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0035_remove_paymenthistory_creation_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='is_payment',
        ),
        migrations.AddField(
            model_name='order',
            name='is_payment_on',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
