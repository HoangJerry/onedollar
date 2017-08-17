# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0008_product_unique_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='note_yourself',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
    ]
