# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0017_auto_20170814_0955'),
    ]

    operations = [
        migrations.AddField(
            model_name='onedollaruser',
            name='total_order',
            field=models.IntegerField(default=0),
        ),
    ]
