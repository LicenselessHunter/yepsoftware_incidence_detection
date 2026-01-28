from django.contrib import admin
from django.urls import path
from . import views #Referencio al archivo views para usar sus funciones.

app_name = 'incidences'

urlpatterns = [
    path('<slug>/disponibility_report_list', views.disponibility_report_list, name='disponibility_report_list'),
    path('<slug>/stock_prices_report_list', views.stock_prices_report_list, name='stock_prices_report_list'),
    path('<slug>/disponibility_report/', views.disponibility_report, name='disponibility_report'),
    path('<slug>/stock_prices_report/', views.stock_prices_report, name='stock_prices_report'),
]