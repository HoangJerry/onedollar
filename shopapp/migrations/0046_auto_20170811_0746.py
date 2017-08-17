# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0045_auto_20170811_0744'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='categorytest',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='categorytest',
            name='parent',
        ),
        migrations.DeleteModel(
            name='CategoryTest',
        ),
    ]
