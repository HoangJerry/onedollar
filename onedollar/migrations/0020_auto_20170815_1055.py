# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0019_auto_20170815_1054'),
    ]

    operations = [
        migrations.AlterField(
            model_name='onedollaruser',
            name='total_order',
            field=models.IntegerField(default=0),
        ),
    ]
