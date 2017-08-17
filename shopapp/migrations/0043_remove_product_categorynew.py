# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0042_auto_20170811_0335'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='categorynew',
        ),
    ]
