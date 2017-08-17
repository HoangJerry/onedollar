# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='onedollaruser',
            name='is_create_product',
            field=models.BooleanField(default=False),
        ),
    ]
