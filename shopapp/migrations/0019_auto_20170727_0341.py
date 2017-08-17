# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0018_auto_20170727_0338'),
    ]

    operations = [
        migrations.RenameField(
            model_name='product',
            old_name='categorynew',
            new_name='category_new',
        ),
    ]
