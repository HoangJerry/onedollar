# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0007_auto_20170714_0245'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='unique_id',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
    ]
