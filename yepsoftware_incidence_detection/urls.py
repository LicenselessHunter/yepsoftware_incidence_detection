
from django.contrib import admin
from django.urls import path, include
from . import views #Referencio al archivo views para usar sus funciones.

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('accounts/', include('accounts.urls')), #Se incluye el archivo "Accounts.urls" y con ello acceso a sus url. en la pagina.
    path('products/', include('products.urls')), # Incluyo las URLs de la app products
    path('incidences/', include('incidences.urls')),
]