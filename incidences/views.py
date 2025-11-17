from django.conf import settings
from django.shortcuts import render, redirect
from .models import incidence_report, product_incidence_group, unsellable_incidence, no_stock_incidence, price_incidence, special_price_incidence
from products.models import product, marketplace

import json #Python has a built-in package called json, which can be used to work with JSON data.
import requests
import urllib.parse
from hashlib import sha256
from hmac import HMAC
from datetime import datetime

from . import resources
from tablib import Dataset #Tablib is an MIT Licensed format-agnostic tabular dataset library, written in Python. It allows you to import, export, and manipulate tabular data sets. Advanced features include, segregation, dynamic columns, tags & filtering, and seamless format import & export. Se combinara con bilbioteca 'django-import-export'
import pandas as pd
from io import BytesIO
from django.contrib import messages
from django.http import HttpResponse

from bs4 import BeautifulSoup
import cloudscraper #A simple Python module to bypass Cloudflare's anti-bot page (also known as "I'm Under Attack Mode", or IUAM), implemented with Requests. Cloudflare's anti-bot page currently just checks if the client supports Javascript, though they may add additional techniques in the future.

from django.contrib.auth.decorators import login_required #Se importa el decorator.

# Create your views here.
@login_required
def falabella_product_disponibility(request):

    last_incidence_report = incidence_report.objects.filter(marketplace_id__marketplace_name='Falabella', report_type='not sellable with stock').last()
    
    if request.method == 'POST' and 'export_report' in request.POST:
        disponibility_report_resource = resources.disponibility_report_export()
        dataset = disponibility_report_resource.export(current_report=last_incidence_report)

        response = HttpResponse(dataset.xlsx)
        response['Content-Disposition'] = f'attachment; filename="falabella N°{last_incidence_report.report_number} disponibilidad {last_incidence_report.report_date_time.strftime("%Y-%m-%d %H:%M:%S")}.xlsx"' #An f-string allows you to embed Python expressions directly inside string literals by enclosing them in curly braces {}. When the code is executed, Python replaces the expressions inside the braces with their resulting values. Aquí se usa para insertar variables dentro del string que define el nombre del archivo exportado.

        #The strftime() method in Python is used to format datetime or time objects into a string representation based on a specified format. The name "strftime" stands for "string format time." This method is part of the datetime module and is commonly used for converting date and time information into a human-readable and customizable string. 

        return response


    if request.method == 'POST' and 'initiate_report' in request.POST:

        falabella_products_queryset = product.objects.filter(marketplace_id__marketplace_name='Falabella')
        selected_item_skus = str(list(falabella_products_queryset.values_list('sku', flat=True))).replace("'",'"')

        products_dict = falabella_api_configuration(selected_item_skus)
        marketplace_instance = marketplace.objects.get(marketplace_name='Falabella')

        if last_incidence_report:
            new_report = incidence_report.objects.create(marketplace_id=marketplace_instance, report_number=last_incidence_report.report_number + 1, report_type='not sellable with stock', inspected_products=len(products_dict), created_by=request.user)

        else:
            new_report = incidence_report.objects.create(marketplace_id=marketplace_instance, report_number=1, report_type='not sellable with stock', inspected_products=len(products_dict), created_by=request.user)

        for product_item in products_dict:

            products_dict_url = product_item['Url']
            products_dict_sku = product_item['SellerSku']
            products_dict_stock = product_item['BusinessUnits']['BusinessUnit']['Stock']
            product_instance = falabella_products_queryset.get(sku=products_dict_sku)


            #---- A TRAVÉS DE SCRAPING, SE VERÍFICA QUE EL BOTÓN DE COMPRA ESTÉ HABILITADO PARA EL PRODUCTO. ----#
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'}
            # User-Agent --> El User-Agent request header es una cadena característica que le permite a los servidores y servicios de red identificar la aplicación, sistema operativo, compañía, y/o la versión del user agent que hace la petición. La identificación de agente de usuario es uno de los criterios de exclusión utilizado por el estándar de exclusión de robots para impedir el acceso a ciertas secciones de un sitio web, de lo contrario, madaría error 403.

            scraper = cloudscraper.create_scraper() # returns a CloudScraper instance
            page = scraper.get(products_dict_url, headers=headers)
            #Si no le agrego el user-agent, provoca que el cloudscrapper a veces falle.

            soup = BeautifulSoup(page.text, "html.parser")
            
            purchase_button = soup.find(id="add-to-cart-button") #Se busca el botón de compra.

            if purchase_button == None and int(products_dict_stock) > 0:
                incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=products_dict_url)

                unsellable_incidence.objects.create(incidence_group_id=incidence_group, stock=products_dict_stock)

        messages.success(request, 'El informe de disponibilidad de productos ha sido generado correctamente.')
            
        return redirect('incidences:falabella_product_disponibility')


    try:
        not_available_products_queryset = product_incidence_group.objects.filter(incidence_report_id=last_incidence_report.id)
        not_available_products_count = not_available_products_queryset.count()
        available_products_count = last_incidence_report.inspected_products - not_available_products_count

        not_available_incidences = unsellable_incidence.objects.filter(incidence_group_id__in=not_available_products_queryset)
        incidence_groups = product_incidence_group.objects.filter(incidence_report_id=last_incidence_report.id)

        context = {
            'last_incidence_report': last_incidence_report,
            'not_available_products_count': not_available_products_count,
            'available_products_count': available_products_count,
            'not_available_incidences': not_available_incidences,
            'incidence_groups': incidence_groups,
        }

        return render(request, 'incidences/disponibility_report.html', context)
    
    except:
        return render(request, 'incidences/disponibility_report.html')


@login_required
def falabella_stock_prices_report(request):
    last_incidence_report = incidence_report.objects.filter(marketplace_id__marketplace_name='Falabella', report_type='incorrect prices / no stock').last()

    if request.method == 'POST' and 'export_report' in request.POST:
        excel_sheets_dict = {}

        
        if (no_stock_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report)).exists():
            stock_prices_resource = resources.stock_prices_report_export()
            no_stock_data = stock_prices_resource.export(current_report=last_incidence_report) #Prepare tablib.Dataset for no_stock_incidence
            df_no_stock = pd.DataFrame(no_stock_data.dict) #Convertir Dataset a un DataFrame de Pandas
            excel_sheets_dict['no_stock_sheet'] = [df_no_stock, 'Sin Stock']


        
        if (price_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report)).exists():
            normal_prices_resource = resources.normal_prices_report_export()
            price_data = normal_prices_resource.export(current_report=last_incidence_report) #Prepare tablib.Dataset for price_incidence
            df_prices = pd.DataFrame(price_data.dict) #Convertir Dataset a un DataFrame de Pandas
            excel_sheets_dict['prices_sheet'] = [df_prices, 'Precios Normales']


        
        if (special_price_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report)).exists():
            special_prices_resource = resources.special_prices_report_export()
            special_price_data = special_prices_resource.export(current_report=last_incidence_report) #Prepare tablib.Dataset for special_price_incidence
            df_special_prices = pd.DataFrame(special_price_data.dict) #Convertir Dataset a un DataFrame de Pandas
            excel_sheets_dict['special_prices_sheet'] = [df_special_prices, 'Precios Descuento']


        output = BytesIO() #Es una clase en Python del módulo io que crea un buffer en memoria para datos binarios, comportándose como un archivo virtual para operaciones de lectura y escritura de bytes. Se utiliza para manipular datos binarios como imágenes o archivos, en lugar de texto, y es útil cuando se necesita procesar datos en memoria sin necesidad de un archivo físico. 
        
        # Usar un ExcelWriter de pandas para escribir en múltiples hojas
        # Class for writing DataFrame objects into excel sheets. En el primer argumento, se especifica la ruta del archivo xls o xlsx en donde se va a escribir, en este caso, el archivo que está en el buffer de memoria creado con "BytesIO". 
        with pd.ExcelWriter(output) as writer:
            for key in excel_sheets_dict:
                excel_sheets_dict[key][0].to_excel(writer, sheet_name=excel_sheets_dict[key][1], index=False)

        
        # Preparar la respuesta HTTP para la descarga
        output.seek(0) # Rebobinar el buffer al inicio. Se usa para mover el cursor de un archivo a la posición inicial (byte 0). Es útil para volver a leer o escribir desde el principio de un archivo sin tener que cerrarlo y volver a abrirlo. Si tienes un archivo abierto y necesitas leerlo de nuevo desde el principio, puedes usar archivo.seek(0).  
        response = HttpResponse(
            output
        )
        response['Content-Disposition'] = f'attachment; filename="falabella N°{last_incidence_report.report_number} precio/stock {last_incidence_report.report_date_time.strftime("%Y-%m-%d %H:%M:%S")}.xlsx"'

        return response

    if request.method == 'POST' and 'initiate_report' in request.POST:

        falabella_products_queryset = product.objects.filter(marketplace_id__marketplace_name='Falabella')
        selected_item_skus = str(list(falabella_products_queryset.values_list('sku', flat=True))).replace("'",'"')

        products_dict = falabella_api_configuration(selected_item_skus)
        marketplace_instance = marketplace.objects.get(marketplace_name='Falabella')

        if last_incidence_report:
            new_report = incidence_report.objects.create(marketplace_id=marketplace_instance, report_number=last_incidence_report.report_number + 1, report_type='incorrect prices / no stock', inspected_products=len(products_dict), created_by=request.user)

        else:
            new_report = incidence_report.objects.create(marketplace_id=marketplace_instance, report_number=1, report_type='incorrect prices / no stock', inspected_products=len(products_dict), created_by=request.user)

        for product_item in products_dict:
            products_dict_url = product_item['Url']
            products_dict_sku = product_item['SellerSku']
            products_dict_price = int(float(product_item['BusinessUnits']['BusinessUnit']['Price']))

            try:
                products_dict_special_price = int(float(product_item['BusinessUnits']['BusinessUnit']['SpecialPrice']))

            except:
                #Por sí el precio de descuento es un string vacío en falabella.
                products_dict_special_price = None

            products_dict_stock = int(product_item['BusinessUnits']['BusinessUnit']['Stock'])
            product_instance = falabella_products_queryset.get(sku=products_dict_sku)

            if products_dict_stock <= 0:
                incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=products_dict_url)

                no_stock_incidence.objects.create(incidence_group_id=incidence_group, stock=products_dict_stock)

            if products_dict_price != product_instance.normal_price:

                try:
                    incidence_group = product_incidence_group.objects.get(incidence_report_id=new_report, product_id=product_instance)

                except:
                    incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=products_dict_url)

                    price_incidence.objects.create(incidence_group_id=incidence_group, local_price=product_instance.normal_price, marketplace_price=products_dict_price)

                else:
                    price_incidence.objects.create(incidence_group_id=incidence_group, local_price=product_instance.normal_price, marketplace_price=products_dict_price)

            if products_dict_special_price != product_instance.special_price:
                try:
                    incidence_group = product_incidence_group.objects.get(incidence_report_id=new_report, product_id=product_instance)

                except:
                    incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=products_dict_url)

                    special_price_incidence.objects.create(incidence_group_id=incidence_group, special_local_price=product_instance.special_price, special_marketplace_price=products_dict_special_price)

                else:
                    special_price_incidence.objects.create(incidence_group_id=incidence_group, special_local_price=product_instance.special_price, special_marketplace_price=products_dict_special_price)

        messages.success(request, 'El informe de stock y precios ha sido generado correctamente.')
            
        return redirect('incidences:falabella_stock_prices_report')


    try:
        products_without_stock = no_stock_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report)
        price_incidences = price_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report)
        special_price_incidences = special_price_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report)
        incidence_groups = product_incidence_group.objects.filter(incidence_report_id=last_incidence_report.id)

        context = {
            'last_incidence_report': last_incidence_report,
            'products_without_stock': products_without_stock,
            'price_incidences': price_incidences,
            'special_price_incidences': special_price_incidences,
            'incidence_groups': incidence_groups,
        }

        return render(request, 'incidences/stock_prices_report.html', context)
    
    except:
        return render(request, 'incidences/stock_prices_report.html')


def falabella_api_configuration(selected_item_skus):
        url = settings.FAL_URL
        api_key = settings.FAL_API_KEY

        # Request parameters
        parameters = {
            'UserID': settings.FAL_USER_ID, #El ID del usuario que realiza la llamada. La lista de usuarios autorizados se mantiene en la interfaz web de SellerCenter en Configuración general / Administrar usuarios.
            'Version': '1.0', #La versión de API contra la que se ejecutará esta llamada, en formato mayor-punto-menor. Actualmente debe ser 1.0, aunque la versión real de la API es 2.6.20. Si se omite, se devuelve un mensaje de error
            'Action': 'GetProducts', #Nombre de la función que se va a llamar. Obligatorio.
            'Format': 'JSON',
            'Timestamp': datetime.now().isoformat(),  # Current time in ISO format. La hora actual en formato ISO8601 relativa a UTC (p. Ej., Marca de tiempo = 2015-04-01T10: 00: 00 + 02: 00 para Berlín), de modo que las llamadas no puedan ser reproducidas por un tercero que espíe (es decir, aquellas llamadas demasiado lejos en el pasado o en el futuro producen un mensaje de error). Obligatorio.
            #'SkuSellerList': '["YEP3070","1036-3B CLASIC","YEP1022-3+","YEP1022-2","YEP3020","1036-1CLASIC","YEP1020","YEP3080","YEP1017","YEP1016"]', #Devuelve aquellos productos donde la cadena de búsqueda está contenida en el nombre y / o SKU del producto.
            'SkuSellerList': selected_item_skus, #Se convierte el QuerySet en una lista de strings.
            'Filter': 'all'
        }

        # Generate the signature and add it to the parameters
        parameters['Signature'] = generate_signature(api_key, parameters.copy())

        headers = {
            "accept": "application/json",
            "Content-type": "application/json",
            "User-Agent": settings.FAL_USER_AGENT #SELLER_ID/TECNOLOGÍA_USADA/VERSIÓN_TECNOLOGÍA/TIPO_INTEGRACIÓN/CÓDIGO_UNIDAD_DE_NEGOCIO
        }

        # Make the GET request to the APIs
        response = requests.get(url, headers=headers, params=parameters)

        json_to_python_dict = json.loads(response.text) #json.loads() is a function within Python's built-in json module used to deserialize a JSON-formatted string into a Python object. Va a convertir el objeto JSON en un diccionario de python.
        products_dict = json_to_python_dict['SuccessResponse']['Body']['Products']['Product']

        return products_dict


def generate_signature(api_key, parameters):
    """
    Generates an HMAC-SHA256 signature for API requests.

    Args:
        api_key (str): Your API key provided by the service.
        parameters (dict): A dictionary containing request parameters.

    Returns:
        str: The generated signature in hexadecimal format


        
    La cadena para firmar es ...

    el resultado concatenado de todos los parámetros de la solicitud,
    ordenados por nombre,
    incluyendo parámetros opcionales,
    y excluyendo el parámetro Signature.
    Los nombres y valores deben estar codificados en la URL de acuerdo con el estándar RFC 3986, concatenados con el carácter '='. Cada conjunto de parámetros (nombre = valor) debe separarse con el carácter '&'.
    """
    # Sort the parameters alphabetically
    sorted_params = sorted(parameters.items())

    # Concatenate the parameters into URL format
    concatenated = urllib.parse.urlencode(sorted_params, quote_via=urllib.parse.quote)

    # Generate the HMAC-SHA256 signature
    signature = HMAC(api_key.encode('utf-8'), concatenated.encode('utf-8'), sha256).hexdigest()
    return signature