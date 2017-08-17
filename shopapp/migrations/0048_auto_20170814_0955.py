# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0047_auto_20170814_0940'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='category',
            field=models.ForeignKey(related_name='shopproduct', blank=True, to='onedollar.CategoryTest', null=True),
        ),
    ]
