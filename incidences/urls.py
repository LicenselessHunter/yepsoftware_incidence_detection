from django.contrib import admin
from django.urls import path
from . import views #Referencio al archivo views para usar sus funciones.

app_name = 'incidences'

urlpatterns = [
    path('falabella_product_disponibility/', views.falabella_product_disponibility, name='falabella_product_disponibility'),
    path('falabella_stock_prices_report/', views.falabella_stock_prices_report, name='falabella_stock_prices_report'),
    path('lider_stock_prices_report/', views.lider_stock_prices_report, name='lider_stock_prices_report'),
]