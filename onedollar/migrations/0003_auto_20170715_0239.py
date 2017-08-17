# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0002_onedollaruser_is_create_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='onedollaruser',
            name='collect_your_cash_4h_24h',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='onedollaruser',
            name='enter_his_address_after_8h_48h',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='onedollaruser',
            name='second_chance_4h_48h',
            field=models.IntegerField(default=0),
        ),
    ]
