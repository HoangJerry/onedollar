# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('shopapp', '0019_auto_20170727_0341'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('payment_history', models.CharField(max_length=100, null=True, blank=True)),
                ('merchant', models.ForeignKey(related_name='merchant', editable=False, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
