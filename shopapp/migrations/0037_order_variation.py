# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0036_auto_20170803_0930'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='variation',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
    ]
