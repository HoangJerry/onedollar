# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0005_remove_onedollaruser_free_daily_cat_now'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='no_of_days',
            field=models.PositiveSmallIntegerField(null=True, verbose_name='Number of hours:', blank=True),
        ),
    ]
