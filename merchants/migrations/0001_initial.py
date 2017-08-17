# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EmailFags',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('receive_an_order', models.BooleanField(default=True)),
                ('approve_a_new_product', models.BooleanField(default=True)),
                ('received_a_payment_product', models.BooleanField(default=True)),
                ('do_not_send_me_any_of_these_emails', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Store',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.PositiveSmallIntegerField(default=10, choices=[(0, 'Enabled'), (10, 'Blocked'), (20, 'Deleted')])),
                ('store_platform', models.CharField(max_length=50, null=True, blank=True)),
                ('url_store_platform', models.CharField(max_length=200, null=True, blank=True)),
                ('revenue_last_year', models.FloatField(null=True, blank=True)),
                ('warehouse_located', models.CharField(max_length=50, null=True, blank=True)),
                ('warehouse_street', models.CharField(max_length=200, null=True, blank=True)),
                ('product_categories', models.CharField(max_length=200, null=True, blank=True)),
                ('provider_payment', models.CharField(max_length=200, null=True, blank=True)),
                ('email_payment', models.CharField(max_length=200, null=True, blank=True)),
            ],
        ),
    ]
