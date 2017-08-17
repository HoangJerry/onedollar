# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0022_auto_20170728_0415'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymenthistory',
            name='status',
            field=models.SmallIntegerField(default=0, choices=[(0, 'Upcoming'), (10, 'Pending'), (20, 'Completed')]),
        ),
    ]
