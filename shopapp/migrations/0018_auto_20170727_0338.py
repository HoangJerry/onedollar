# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0009_categorynew'),
        ('shopapp', '0017_auto_20170727_0322'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='categorynew',
            field=models.ForeignKey(related_name='shopproductcategory', blank=True, to='onedollar.CategoryNew', null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='creator',
            field=models.ForeignKey(related_name='creator', to=settings.AUTH_USER_MODEL),
        ),
    ]
