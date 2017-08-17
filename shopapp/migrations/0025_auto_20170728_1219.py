# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0024_product_brand'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paymenthistory',
            name='merchant',
        ),
        migrations.RemoveField(
            model_name='product',
            name='brand',
        ),
        migrations.AlterField(
            model_name='product',
            name='category_new',
            field=models.ForeignKey(blank=True, to='onedollar.CategoryNew', null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='creator',
            field=models.ForeignKey(related_name='shopproduct', to=settings.AUTH_USER_MODEL),
        ),
        migrations.DeleteModel(
            name='PaymentHistory',
        ),
    ]
