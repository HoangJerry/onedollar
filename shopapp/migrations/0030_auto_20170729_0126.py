# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0011_auto_20170728_1219'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('shopapp', '0029_product_category_new'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('payment_history', models.CharField(max_length=100, null=True, blank=True)),
                ('total_amount', models.IntegerField(default=0, null=True, blank=True)),
                ('status', models.SmallIntegerField(default=0, choices=[(0, 'Upcoming'), (10, 'Pending'), (20, 'Completed')])),
                ('merchant', models.ForeignKey(related_name='merchant', editable=False, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RemoveField(
            model_name='categorynew',
            name='category',
        ),
        migrations.RemoveField(
            model_name='product',
            name='category_new',
        ),
        migrations.AddField(
            model_name='product',
            name='category_child',
            field=models.ForeignKey(related_name='shopproductlala', blank=True, to='onedollar.CategoryNew', null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='brand',
            field=models.ForeignKey(related_name='shopproducthehe', blank=True, to='onedollar.Brand', null=True),
        ),
        migrations.DeleteModel(
            name='CategoryNew',
        ),
    ]
