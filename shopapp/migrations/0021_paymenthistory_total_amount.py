# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0020_paymenthistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymenthistory',
            name='total_amount',
            field=models.IntegerField(default=0),
        ),
    ]
