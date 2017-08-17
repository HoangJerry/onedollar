# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0040_remove_product_category_child'),
        ('onedollar', '0011_auto_20170728_1219'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='categorynew',
            name='category',
        ),
        migrations.DeleteModel(
            name='CategoryNew',
        ),
    ]
