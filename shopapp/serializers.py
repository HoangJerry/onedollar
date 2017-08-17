from rest_framework import fields, serializers

from onedollar.serializers import LiteUserSerializer, PhotoSerializer, CategoryTestSerializer
from onedollar import models as onedollar_models
import datetime as dt
import categories

from .models import *
import json
import ast

class UniquesUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unique
        fields = ('unique_id','quantity','buying_price','shipping_cost')


class UniqueSerializer(serializers.ModelSerializer):
    class Meta(UniquesUpdateSerializer.Meta):
        fields = UniquesUpdateSerializer.Meta.fields + ('id','size','color','product_sold')

class ProductListSerializer(serializers.ModelSerializer):
    photos = PhotoSerializer(many=True, read_only=True)
    uniques = UniqueSerializer(many=True, read_only=True)
    category = CategoryTestSerializer()
    brand = serializers.StringRelatedField()
    creation_date = serializers.DateTimeField(format='%m/%d/%Y', input_formats=['%m/%d/%Y'], read_only=True)
    shipping = serializers.SerializerMethodField('_shipping')
    store = serializers.StringRelatedField(source='creator', read_only=True)
    colors = serializers.MultipleChoiceField(choices=Product.COLORS)
    sizes = serializers.MultipleChoiceField(choices=Product.SIZES)
    reward_tokens = serializers.IntegerField(required=False)

    class Meta:
        model = Product
        fields = ('id','creator','title', 'category', 'photos','brand','store',
                'creation_date', 'retail_price', 'buying_price', 'reward_tokens',
                'shipping','shipping_time','shipping_cost','unique_id','uniques','colors','sizes',)

    def _shipping(self, obj):
        return obj.get_shipping_time_display()

class ProductCreateSerializer(ProductListSerializer):
    photos = PhotoSerializer(many=True, read_only=True)
    creator = LiteUserSerializer(required=False, read_only=True)
    colors = serializers.MultipleChoiceField(choices=Product.COLORS)
    sizes = serializers.MultipleChoiceField(choices=Product.SIZES)
    category = serializers.StringRelatedField()
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ('tags','description', 'creator', 'colors', 
                'sizes', 'orders_count')

    def create(self, validated_data,user=None):
        product = Product(**validated_data)
        product.creation_date = dt.datetime.now()
        product.category = onedollar_models.CategoryTest.objects.filter(id=self.initial_data['category'])[0]
        if self.initial_data['brand']:
            product.brand = onedollar_models.Brand.objects.filter(id=self.initial_data['brand'])[0]
        product.save()


        uniques = self.initial_data.getlist('uniques')
        for unique in uniques:
            # temp = json.load(str(unique))
            # print temp.unique_id
            temp = ast.literal_eval(unique)
            product_unique=Unique(unique_id=temp['unique_id'],product=product,
                size=temp['size'],color=temp['color'],quantity=temp['quantity'],
                buying_price=temp['buying_price'],shipping_cost=product.shipping_cost)
            product_unique.save()

        product.country.add(user.country)

        photos = self.initial_data.getlist('photos')
        product_photos = []
        for photo in photos:
            product_photo = ProductPhoto(product=product)
            product_photo.image.save(photo.name, photo)
        return product

class ProductSerializer(ProductListSerializer):
    creator = LiteUserSerializer(required=False, read_only=True)

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ('status','description', 'creator', 'colors', 
                'sizes', 'orders_count')

class OrderSerializer(serializers.ModelSerializer):
    user = LiteUserSerializer(read_only=True)
    product_obj = ProductListSerializer(source='product', read_only=True)
    amount = serializers.ReadOnlyField()
    reward_tokens = serializers.ReadOnlyField()
    updated_credits = serializers.SerializerMethodField('_updated_credits')
    delivery_status_display = serializers.SerializerMethodField('_delivery_status')

    class Meta:
        model = Order

    def _updated_credits(self, obj):
        try:
            return onedollar_models.OneDollarUser.objects.filter(
                    pk=self.context['request'].user.id).first().total_credits
        except Exception as e:
            return 0

    def _delivery_status(self, obj):
        return obj.get_delivery_status_display()

class PaymentHistorySerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField('_status')
    # status = serializers.StringRelatedField()
    class Meta:
        model = PaymentHistory

    def _status(self, obj):
        return obj.get_status_display()

class CategorySerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField('_name')
    class Meta:
        model = categories.models.Category

    def _name(self, obj):
        link = str(obj.get_absolute_url()).title()[1:]
        return link.replace("/", ", ")