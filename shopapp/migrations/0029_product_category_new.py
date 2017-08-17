# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0028_categorynew'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='category_new',
            field=models.ForeignKey(blank=True, to='shopapp.CategoryNew', null=True),
        ),
    ]
