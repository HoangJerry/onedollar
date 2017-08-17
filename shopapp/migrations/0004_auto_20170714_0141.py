# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0003_auto_20170714_0137'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='unique_id',
        ),
        migrations.AddField(
            model_name='product',
            name='unique',
            field=models.ManyToManyField(related_name='unique', to='shopapp.Unique'),
        ),
    ]
