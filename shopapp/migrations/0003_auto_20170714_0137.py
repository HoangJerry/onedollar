# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0002_auto_20170712_0405'),
    ]

    operations = [
        migrations.CreateModel(
            name='Unique',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=100, null=True, blank=True)),
                ('size', models.CharField(max_length=10, null=True, blank=True)),
                ('color', models.CharField(max_length=10, null=True, blank=True)),
                ('quantity', models.IntegerField(default=0, null=True, blank=True)),
                ('product_sold', models.IntegerField(default=0, null=True, blank=True)),
            ],
        ),
        migrations.AlterField(
            model_name='product',
            name='status',
            field=models.SmallIntegerField(default=20, choices=[(0, 'Disable'), (10, 'Enable'), (20, 'Pending'), (30, 'Approved'), (40, 'Rejected')]),
        ),
        migrations.RemoveField(
            model_name='product',
            name='unique_id',
        ),
        migrations.AddField(
            model_name='product',
            name='unique_id',
            field=models.ManyToManyField(related_name='unique_id', to='shopapp.Unique'),
        ),
    ]
