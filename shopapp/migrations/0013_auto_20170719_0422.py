# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0012_auto_20170718_0320'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='reward_tokens',
            field=models.IntegerField(default=0),
        ),
    ]
