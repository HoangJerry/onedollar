# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0046_auto_20170811_0746'),
    ]

    operations = [
        migrations.RenameField(
            model_name='product',
            old_name='category_new',
            new_name='category_child',
        ),
    ]
