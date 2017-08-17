# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0011_auto_20170728_1219'),
        ('shopapp', '0027_remove_product_category_new'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryNew',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50, verbose_name='name')),
                ('category', models.ForeignKey(related_name='categoryparent', blank=True, to='onedollar.Category', null=True)),
            ],
        ),
    ]
