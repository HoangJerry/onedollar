# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0004_onedollaruser_free_daily_cat_now'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='onedollaruser',
            name='free_daily_cat_now',
        ),
    ]
