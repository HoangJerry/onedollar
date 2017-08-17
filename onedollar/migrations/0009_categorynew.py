# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('onedollar', '0008_auto_20170726_0742'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryNew',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('modification_date', models.DateTimeField(auto_now=True)),
                ('status', models.SmallIntegerField(default=0, choices=[(0, 'Disable'), (10, 'Enable')])),
                ('name', models.CharField(max_length=50, verbose_name='name')),
                ('category', models.ForeignKey(blank=True, to='onedollar.Category', null=True)),
                ('creator', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
