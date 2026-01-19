from django.contrib import admin
from django.urls import path
from . import views #Referencio al archivo views para usar sus funciones.

app_name = 'incidences'

urlpatterns = [
    path('<slug>/disponibility_report_list', views.disponibility_report_list, name='disponibility_report_list'),
    path('falabella_product_disponibility/', views.falabella_product_disponibility, name='falabella_product_disponibility'),
    path('falabella_stock_prices_report/', views.falabella_stock_prices_report, name='falabella_stock_prices_report'),
    path('lider_stock_prices_report/', views.lider_stock_prices_report, name='lider_stock_prices_report'),
    path('paris_product_disponibility/', views.paris_product_disponibility, name='paris_product_disponibility'),
    path('paris_stock_prices_report/', views.paris_stock_prices_report, name='paris_stock_prices_report'),
]