from rest_framework.viewsets import ModelViewSet

from catalogue.helpers.HttpException import HttpException
from catalogue.helpers.HttpResponseHandler import HTTP
from catalogue.models.category import Category
from catalogue.serializers.categorySerializer import CategorySerializer


class CategoryViewSet(ModelViewSet):

    def list(self, request):
        try:

            query = Category.objects.all()
            data = CategorySerializer(query, many=True).to_representation(query)
            return HTTP.response(200, 'Catalogue View', data)

        except HttpException as e:
            return HTTP.response(e.http_code, e.http_detail)
        except Exception as e:
            return HTTP.response(400, 'Some error occurred. {}. {}.'.format(type(e).__name__, str(e)))

    def create(self, request):
        return HTTP.response(405, 'You are not allowed in here son, GTFO')
