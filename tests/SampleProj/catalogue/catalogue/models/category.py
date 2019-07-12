from django.db import models


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=256)

    objects = models.Manager()

    class Meta:
        db_table = 'CATEGORY'
        ordering = ['-id']
