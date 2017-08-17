# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0018_onedollaruser_total_order'),
    ]

    operations = [
        migrations.AlterField(
            model_name='onedollaruser',
            name='total_order',
            field=models.IntegerField(default=b'default_total_order'),
        ),
    ]
