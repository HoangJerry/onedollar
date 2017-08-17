# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import multiselectfield.db.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('onedollar', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CoinCount',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('count_for', models.SmallIntegerField(default=0, choices=[(0, 'swap'), (10, 'another')])),
                ('count', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.FloatField()),
                ('reward_tokens', models.IntegerField()),
                ('channel', models.SmallIntegerField(blank=True, null=True, choices=[(1, 'PayPal'), (2, 'Stripe')])),
                ('transaction_code', models.CharField(max_length=50, null=True, blank=True)),
                ('transaction_id', models.CharField(max_length=50, null=True, blank=True)),
                ('payer_firstname', models.CharField(max_length=50, null=True, blank=True)),
                ('payer_lastname', models.CharField(max_length=50, null=True, blank=True)),
                ('payer_email', models.CharField(max_length=100, null=True, blank=True)),
                ('firstname', models.CharField(max_length=50, null=True, blank=True)),
                ('lastname', models.CharField(max_length=50, null=True, blank=True)),
                ('email', models.CharField(max_length=100, null=True, blank=True)),
                ('phone', models.CharField(max_length=20, null=True, blank=True)),
                ('street1', models.CharField(max_length=300, null=True, blank=True)),
                ('street2', models.CharField(max_length=300, null=True, blank=True)),
                ('postal_code', models.CharField(max_length=10, null=True, blank=True)),
                ('province', models.CharField(max_length=100, null=True, blank=True)),
                ('city', models.CharField(max_length=100, null=True, blank=True)),
                ('delivery_status', models.SmallIntegerField(default=0, choices=[(0, 'New'), (10, 'Processing'), (20, 'Shipping'), (30, 'Arrived'), (40, 'Not sent'), (50, 'Blocked or Fraud')])),
                ('shipping_time', models.PositiveSmallIntegerField(blank=True, null=True, choices=[(0, b'0'), (1, b'5 - 10'), (2, b'7 - 14'), (3, b'10 - 15'), (4, b'14 - 21'), (5, b'21 - 18')])),
                ('tracking_number', models.CharField(max_length=100, null=True, blank=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('country', models.ForeignKey(blank=True, to='onedollar.Country', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation_date', models.DateTimeField()),
                ('modification_date', models.DateTimeField(auto_now=True)),
                ('status', models.SmallIntegerField(default=20, choices=[(0, 'Disable'), (10, 'Enable'), (20, 'Pending'), (30, 'Approved'), (10, 'Rejected')])),
                ('unique_id', models.CharField(max_length=50, null=True, blank=True)),
                ('title', models.CharField(max_length=200, verbose_name='title')),
                ('description', models.TextField(verbose_name='description')),
                ('quantity', models.PositiveIntegerField(help_text='Skip this field to make the quantity unlimited', null=True, blank=True)),
                ('colors', multiselectfield.db.fields.MultiSelectField(blank=True, max_length=104, null=True, choices=[(b'white', b'White'), (b'green', b'Green'), (b'beige', b'Beige'), (b'ivory', b'Ivory'), (b'black', b'Black'), (b'grey', b'Grey'), (b'pink', b'Pink'), (b'navyblue', b'Navy Blue'), (b'red', b'Red'), (b'brown', b'Brown'), (b'orange', b'Orange'), (b'purple', b'Purple'), (b'blue', b'Blue'), (b'tan', b'Tan'), (b'yellow', b'Yellow'), (b'gold', b'Gold'), (b'multicolor', b'Multicolor')])),
                ('sizes', multiselectfield.db.fields.MultiSelectField(blank=True, max_length=24, null=True, choices=[(b'xxs', b'XXS'), (b'xs', b'XS'), (b's', b'S'), (b'm', b'M'), (b'l', b'L'), (b'xl', b'XL'), (b'xxl', b'XXL'), (b'xxxl', b'XXXL')])),
                ('shipping_time', models.PositiveSmallIntegerField(choices=[(0, b'0'), (1, b'5 - 10'), (2, b'7 - 14'), (3, b'10 - 15'), (4, b'14 - 21'), (5, b'21 - 28')])),
                ('shipping_cost', models.FloatField(default=0)),
                ('retail_price', models.FloatField()),
                ('reward_tokens', models.PositiveIntegerField()),
                ('buying_price', models.FloatField()),
                ('tags', models.TextField(null=True, blank=True)),
                ('earning', models.FloatField(null=True, editable=False, blank=True)),
                ('delivery_status', models.SmallIntegerField(default=0, choices=[(0, 'New'), (10, 'Pending'), (20, 'Sent'), (30, 'Not sent (no reply)'), (40, 'Not sent (no address)'), (50, 'Blocked or Fraud')])),
                ('ordering_date', models.DateField(null=True, blank=True)),
                ('ordering_tracking', models.CharField(max_length=1000, null=True, blank=True)),
                ('latest_chat_date', models.DateTimeField(verbose_name='latest_chat_date', null=True, editable=False, blank=True)),
                ('should_display_winner_popup', models.BooleanField(default=True)),
                ('should_display_seller_popup', models.BooleanField(default=True)),
                ('orders_count', models.PositiveIntegerField(default=0)),
                ('category', models.ForeignKey(related_name='shopproduct', blank=True, to='onedollar.Category', null=True)),
                ('country', models.ManyToManyField(related_name='shopproduct', to='onedollar.Country')),
                ('creator', models.ForeignKey(related_name='shopproduct', to=settings.AUTH_USER_MODEL)),
                ('product_parent', models.ForeignKey(blank=True, to='shopapp.Product', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ProductPhoto',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('image', models.ImageField(upload_to=b'shop-photos', verbose_name='Picture shall be squared, max 640*640, 500k')),
                ('product', models.ForeignKey(related_name='photos', to='shopapp.Product')),
            ],
        ),
        migrations.AddField(
            model_name='order',
            name='product',
            field=models.ForeignKey(related_name='orders', to='shopapp.Product'),
        ),
        migrations.AddField(
            model_name='order',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
    ]
