# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('merchants', '0002_auto_20170710_0739'),
    ]

    operations = [
        migrations.AlterField(
            model_name='store',
            name='status',
            field=models.PositiveSmallIntegerField(default=30, choices=[(0, 'Enabled'), (10, 'Blocked'), (20, 'Deleted'), (30, 'Not finalized'), (40, 'Pending for approvel')]),
        ),
    ]
