# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0005_auto_20170714_0205'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='unique',
        ),
        migrations.AddField(
            model_name='unique',
            name='product',
            field=models.ForeignKey(related_name='uniques', default=1, to='shopapp.Product'),
            preserve_default=False,
        ),
    ]
