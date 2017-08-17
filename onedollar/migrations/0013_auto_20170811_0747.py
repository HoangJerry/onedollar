# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0012_auto_20170811_0331'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryTest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('slug', models.SlugField(verbose_name='slug')),
                ('active', models.BooleanField(default=True, verbose_name='active')),
                ('type', models.PositiveSmallIntegerField(default=1, verbose_name='type', choices=[(1, 'Bet'), (2, 'Shop')])),
                ('lft', models.PositiveIntegerField(editable=False, db_index=True)),
                ('rght', models.PositiveIntegerField(editable=False, db_index=True)),
                ('tree_id', models.PositiveIntegerField(editable=False, db_index=True)),
                ('level', models.PositiveIntegerField(editable=False, db_index=True)),
                ('parent', mptt.fields.TreeForeignKey(related_name='children', verbose_name='parent', blank=True, to='onedollar.CategoryTest', null=True)),
            ],
            options={
                'ordering': ('tree_id', 'lft'),
                'abstract': False,
            },
        ),
        migrations.AlterUniqueTogether(
            name='categorytest',
            unique_together=set([('parent', 'name')]),
        ),
    ]
