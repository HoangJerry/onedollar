# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('categories', '0003_auto_20170811_0327'),
        ('shopapp', '0041_auto_20170811_0334'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='categorynew',
            field=models.ForeignKey(related_name='shopproduct', blank=True, to='categories.Category', null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.ForeignKey(related_name='shopproduct', blank=True, to='onedollar.Category', null=True),
        ),
    ]
