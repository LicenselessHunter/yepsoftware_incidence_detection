from django.contrib import admin
from django.urls import path
from . import views #Referencio al archivo views para usar sus funciones.

app_name = 'products'

urlpatterns = [
    path('<slug>/product_table', views.products, name='products'),
    path('product_edit/<id>', views.product_edit, name='product_edit'),
    path('product_delete/<id>', views.product_delete, name='product_delete'),
]