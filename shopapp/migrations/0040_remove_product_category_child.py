# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0039_paymenthistory_payout_item_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='category_child',
        ),
    ]
