import os

from django.db import models

from catalogue.models.category import Category


def get_image_path(instance, filename):
    return os.path.join('catalogue', str(instance.title), filename)


class Catalogue(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=256)
    year = models.IntegerField(null=True)
    description = models.CharField(max_length=256)
    category = models.ManyToManyField(Category, null=True)
    image = models.ImageField(upload_to=get_image_path, blank=True, null=True)
    rating = models.FloatField(null=False, default=0)

    objects = models.Manager()

    class Meta:
        db_table = 'CATALOGUE'
        ordering = ['-id']
