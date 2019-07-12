from django.contrib import admin
from .models.category import Category
from .models.catalogue import Catalogue

admin.site.register(Catalogue)
admin.site.register(Category)
