
from django.conf.urls import url, include
from django.conf.urls.static import static
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from catalogue.views.CatalogueView import CatalogueViewSet
from catalogue.views.CategoryView import CategoryViewSet
from catalogue_trailerflix.settings import MEDIA_ROOT, MEDIA_URL

router = DefaultRouter()

router.register(r'catalogue', CatalogueViewSet, 'Catalogue')
router.register(r'category', CategoryViewSet, 'Category')

urlpatterns = [
    path('', include(router.urls))
]
