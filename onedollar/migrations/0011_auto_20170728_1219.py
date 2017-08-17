# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0010_brand'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='brand',
            name='creation_date',
        ),
        migrations.RemoveField(
            model_name='brand',
            name='creator',
        ),
        migrations.RemoveField(
            model_name='brand',
            name='modification_date',
        ),
        migrations.RemoveField(
            model_name='brand',
            name='status',
        ),
        migrations.RemoveField(
            model_name='categorynew',
            name='creation_date',
        ),
        migrations.RemoveField(
            model_name='categorynew',
            name='creator',
        ),
        migrations.RemoveField(
            model_name='categorynew',
            name='modification_date',
        ),
        migrations.RemoveField(
            model_name='categorynew',
            name='status',
        ),
    ]
