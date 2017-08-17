# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0004_auto_20170714_0141'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='unique',
        ),
        migrations.AddField(
            model_name='product',
            name='unique',
            field=models.ForeignKey(related_name='unique', blank=True, to='shopapp.Unique', null=True),
        ),
    ]
