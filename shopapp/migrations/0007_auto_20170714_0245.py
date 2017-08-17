# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0006_auto_20170714_0208'),
    ]

    operations = [
        migrations.RenameField(
            model_name='unique',
            old_name='code',
            new_name='unique_id',
        ),
    ]
