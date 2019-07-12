from rest_framework import serializers

from catalogue.serializers.categorySerializer import CategorySerializer
from ..models.catalogue import Catalogue


class CatalogueSerializer(serializers.ModelSerializer):

    def to_representation(self, obj):
        data = super(CatalogueSerializer, self).to_representation(obj)  # the original data
        return data

    class Meta:
        model = Catalogue
        fields = '__all__'


class CatalogueEventSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)

    def to_representation(self, obj):
        data = super(CatalogueEventSerializer, self).to_representation(obj)  # the original data
        return data

    class Meta:
        model = Catalogue
        fields = '__all__'
