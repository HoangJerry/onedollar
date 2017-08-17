# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('shopapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='colors',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, max_length=104, null=True, choices=[(b'White', b'White'), (b'Green', b'Green'), (b'Beige', b'Beige'), (b'Ivory', b'Ivory'), (b'Black', b'Black'), (b'Grey', b'Grey'), (b'Pink', b'Pink'), (b'NavyBlue', b'Navy Blue'), (b'Red', b'Red'), (b'Brown', b'Brown'), (b'Orange', b'Orange'), (b'Purple', b'Purple'), (b'Blue', b'Blue'), (b'Tan', b'Tan'), (b'Yellow', b'Yellow'), (b'Gold', b'Gold'), (b'Multicolor', b'Multicolor')]),
        ),
        migrations.AlterField(
            model_name='product',
            name='sizes',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, max_length=24, null=True, choices=[(b'XXS', b'XXS'), (b'XS', b'XS'), (b'S', b'S'), (b'M', b'M'), (b'L', b'L'), (b'XL', b'XL'), (b'XXL', b'XXL'), (b'XXXL', b'XXXL')]),
        ),
    ]
