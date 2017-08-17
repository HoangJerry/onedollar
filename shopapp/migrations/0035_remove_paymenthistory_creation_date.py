# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0034_auto_20170731_0429'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymenthistory',
            name='creation_date',
        ),
    ]
