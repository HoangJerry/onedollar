# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0003_auto_20170715_0239'),
    ]

    operations = [
        migrations.AddField(
            model_name='onedollaruser',
            name='free_daily_cat_now',
            field=models.IntegerField(default=0),
        ),
    ]
