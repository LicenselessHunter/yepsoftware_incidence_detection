from django.db import models
from django.contrib.auth.models import User #Se importa el model User que esta implicito en Django.
from django.core.validators import MinValueValidator #Este es un validador que servirá para definir valores mínimos en campos numéricos.


# Create your models here.
class marketplace(models.Model):
    marketplace_name = models.CharField(max_length=100, unique=True, blank=False)
    slug = models.SlugField(null=True, unique=True) #A "slug" is a way of generating a valid URL, generally using data already obtained. For instance, a slug uses the title of an article to generate a URL. Se suele utilizar en las URL para facilitar su lectura, pero también para que sean más fáciles de usar para los motores de búsqueda.

    def __str__(self):   #Esta función va a definir como se van a ver los productos de la base de datos en la sección de admin y en el shell.
        return self.marketplace_name  #En este caso los productos se van a mostrar con sus titulos.

class product(models.Model):
    marketplace_id = models.ForeignKey(marketplace, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, on_delete=models.SET_DEFAULT, default=None, null=True)

    sku = models.CharField(
        max_length=30, 
        blank=False)

    sku_marketplace = models.CharField(
        max_length=30, 
        blank=False)

    product_name = models.CharField(max_length=100)
    normal_price = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    special_price = models.PositiveIntegerField(null=True, blank=True)
    creation_date_time = models.DateTimeField(auto_now_add=True)

    # null=True: This parameter tells the database that the field can store NULL values. For IntegerFields, NULL is the correct way to represent an absence of value in the database.
    # blank=True: This parameter relates to form validation. It indicates that the field is not required when submitting a form, and an empty value will be considered valid.

    def __str__(self):
        return self.sku
