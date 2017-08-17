# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0026_product_brand'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='category_new',
        ),
    ]
