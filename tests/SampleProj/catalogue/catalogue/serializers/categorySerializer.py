from rest_framework import serializers
from ..models.category import Category


class CategorySerializer(serializers.ModelSerializer):

    def to_representation(self, obj):
        data = super(CategorySerializer, self).to_representation(obj)  # the original data
        return data

    class Meta:
        model = Category
        fields = '__all__'

