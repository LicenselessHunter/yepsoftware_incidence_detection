from django.conf import settings
from django.shortcuts import render, redirect
from .models import incidence_report, product_incidence_group, unsellable_incidence, no_stock_incidence, price_incidence, special_price_incidence, not_scrapeable_product, existing_product_not_local
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

import base64
import uuid
import ast
import unidecode

from django.contrib.auth.decorators import login_required #Se importa el decorator.
from django.utils.html import format_html #django.utils.html.format_html is a security-oriented utility function used to construct HTML fragments safely within Python code (like views.py or models.py) without the risk of cross-site scripting (XSS) attacks. 


# Create your views here.
@login_required
def falabella_product_disponibility(request):
    marketplace_instance = marketplace.objects.get(marketplace_name='Falabella')
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
        #selected_item_skus = str(list(falabella_products_queryset.values_list('sku', flat=True))).replace("'",'"')

        response = falabella_api_configuration()

        if response.status_code == 200:
            json_to_python_dict = json.loads(response.text) #json.loads() is a function within Python's built-in json module used to deserialize a JSON-formatted string into a Python object. Va a convertir el objeto JSON en un diccionario de python.

        else:
            messages.error(request, f'Consulta API de falabella dio respuesta: {response.status_code}')
            return redirect('incidences:falabella_product_disponibility')

        
        try:
            json_to_python_dict['SuccessResponse']['Body']['Products']['Product']

        except:
            #Por si hay algún error con respecto a la configuración de la API de falabella.
            falabella_api_error = json_to_python_dict['ErrorResponse']['Head']['ErrorMessage']
            messages.error(request, f'"{falabella_api_error}", consulte a un desarrollador')
            return redirect('incidences:falabella_product_disponibility')

        else:
            products_dict = json_to_python_dict['SuccessResponse']['Body']['Products']['Product']

        #---- Llamada a la función que creará un nuebo objeto del model 'incidence_report' ----
        new_report = generate_incidence_report(marketplace_instance, last_incidence_report, 'not sellable with stock', len(products_dict), request) 

        #---- CREACIÓN DE INSTANCIA DE CLOUDSCRAPER ----
        scraper = cloudscraper.create_scraper(
            delay=10,
            browser={
                'custom': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            }
        ) # returns a CloudScraper instance
        #Los desafios de cloudflare usualmente requeiren de 5 segundos para resolver, cloudscraper ya tiene un delay por solicitud por defecto para esto, pero en ocasiones esto no puede ser sufieciente. Como en mi caso que sbreescribo esto al poner un delay de 10 segundos.
        # User-Agent --> El User-Agent request header es una cadena característica que le permite a los servidores y servicios de red identificar la aplicación, sistema operativo, compañía, y/o la versión del user agent que hace la petición. La identificación de agente de usuario es uno de los criterios de exclusión utilizado por el estándar de exclusión de robots para impedir el acceso a ciertas secciones de un sitio web, de lo contrario, madaría error 403.
        #Con el parámetro 'custom', Cloudscraper also allows you to set your own custom user-agents. This gives you greater control over how your scraper presents itself to the target website. Cloudscraper will attempt to match this user-agent string with known device and browser combinations. If a match is found, it will configure the scraper's headers and ciphers accordingly. If not, it will use a generic set of headers and ciphers.
        #It is recommended to reuse a single cloudscraper instance for multiple requests rather than creating a new one for every single request.


        for product_item in products_dict:
            #---- VERIFICACIÓN SI EL PRODUCTO EXISTE EN LA BASE DE DATOS LOCAL ----
            if product_item['SellerSku'] not in list(falabella_products_queryset.values_list('sku', flat=True)):
                existing_product_not_local.objects.create(incidence_report_id=new_report, sku=product_item['SellerSku'], sku_marketplace=product_item['ShopSku'], product_name=product_item['Name'], product_url=product_item['Url'])
                continue
            #---- FIN VERIFICACIÓN SI EL PRODUCTO EXISTE EN LA BASE DE DATOS LOCAL ----

            products_dict_url = product_item['Url']
            products_dict_sku = product_item['SellerSku']
            products_dict_stock = product_item['BusinessUnits']['BusinessUnit']['Stock']
            product_instance = falabella_products_queryset.get(sku=products_dict_sku)

            if int(products_dict_stock) > 0:

                #---- A TRAVÉS DE SCRAPING, SE VERÍFICA QUE EL BOTÓN DE COMPRA ESTÉ HABILITADO PARA EL PRODUCTO. ----#
                page = scraper.get(products_dict_url)
                
                if page.status_code != 200: #Por si cloudscraper no logra acceder al producto del recorrido actual
                    not_scrapeable_product.objects.create(product_id=product_instance, incidence_report_id=new_report, http_status_code=page.status_code)                   
                    continue

                soup = BeautifulSoup(page.content, "html.parser")

                purchase_button = soup.find(id="add-to-cart-button") #Se busca el botón de compra.


                if purchase_button == None:
                    incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=products_dict_url)

                    unsellable_incidence.objects.create(incidence_group_id=incidence_group, stock=products_dict_stock)


        scraper.close()
        messages.success(request, 'El informe de disponibilidad de productos ha sido generado correctamente.')

        return redirect('incidences:falabella_product_disponibility')


    try:
        not_available_products_queryset = product_incidence_group.objects.filter(incidence_report_id=last_incidence_report.id)
        not_available_products_count = not_available_products_queryset.count()

        not_available_incidences = unsellable_incidence.objects.filter(incidence_group_id__in=not_available_products_queryset)
        incidence_groups = product_incidence_group.objects.filter(incidence_report_id=last_incidence_report.id)
        not_scrapeable_products_queryset = not_scrapeable_product.objects.filter(incidence_report_id=last_incidence_report.id)
        not_existing_products_in_local = existing_product_not_local.objects.filter(incidence_report_id=last_incidence_report.id)

        context = {
            'marketplace_instance': marketplace_instance,
            'last_incidence_report': last_incidence_report,
            'not_available_products_count': not_available_products_count,
            'not_available_incidences': not_available_incidences,
            'not_scrapeable_products': not_scrapeable_products_queryset,
            'incidence_groups': incidence_groups,
            'not_existing_products_in_local': not_existing_products_in_local,
        }

        return render(request, 'incidences/disponibility_report.html', context)

    except:
        return render(request, 'incidences/disponibility_report.html', {'marketplace_instance': marketplace_instance})


@login_required
def falabella_stock_prices_report(request):
    marketplace_instance = marketplace.objects.get(marketplace_name='Falabella')
    last_incidence_report = incidence_report.objects.filter(marketplace_id__marketplace_name='Falabella', report_type='incorrect prices / no stock').last()

    if request.method == 'POST' and 'export_report' in request.POST:
        #---- La función prices_stock_report_export() se encargará de preparar y exportar el archivo de excel con el informe de incidencias stock y precios. ----
        return prices_stock_report_export(marketplace_instance, last_incidence_report)

    if request.method == 'POST' and 'initiate_report' in request.POST:

        falabella_products_queryset = product.objects.filter(marketplace_id__marketplace_name='Falabella')
        #selected_item_skus = str(list(falabella_products_queryset.values_list('sku', flat=True))).replace("'",'"')

        response = falabella_api_configuration()

        if response.status_code == 200:
            json_to_python_dict = json.loads(response.text) #json.loads() is a function within Python's built-in json module used to deserialize a JSON-formatted string into a Python object. Va a convertir el objeto JSON en un diccionario de python.

        else:
            messages.error(request, f'Consulta API de falabella dio respuesta: {response.status_code}')
            return redirect('incidences:falabella_stock_prices_report')

        
        try:
            json_to_python_dict['SuccessResponse']['Body']['Products']['Product']

        except:
            #Por si hay algún error con respecto a la configuración de la API de falabella.
            falabella_api_error = json_to_python_dict['ErrorResponse']['Head']['ErrorMessage']
            messages.error(request, f'"{falabella_api_error}", consulte a un desarrollador')
            return redirect('incidences:falabella_stock_prices_report')

        else:
            products_dict = json_to_python_dict['SuccessResponse']['Body']['Products']['Product']

        #---- Llamada a la función que creará un nuebo objeto del model 'incidence_report' ----
        new_report = generate_incidence_report(marketplace_instance, last_incidence_report, 'incorrect prices / no stock', len(products_dict), request)

        for product_item in products_dict:

            #---- VERIFICACIÓN SI EL PRODUCTO EXISTE EN LA BASE DE DATOS LOCAL ----
            if product_item['SellerSku'] not in list(falabella_products_queryset.values_list('sku', flat=True)):
                existing_product_not_local.objects.create(incidence_report_id=new_report, sku=product_item['SellerSku'], sku_marketplace=product_item['ShopSku'], product_name=product_item['Name'], product_url=product_item['Url'])
                continue
            #---- FIN VERIFICACIÓN SI EL PRODUCTO EXISTE EN LA BASE DE DATOS LOCAL ----

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

            #---- INCIDENCIA STOCK ----
            if products_dict_stock <= 0:
                incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=products_dict_url)

                no_stock_incidence.objects.create(incidence_group_id=incidence_group, stock=products_dict_stock)

            #---- INCIDENCIA PRECIO NORMAL ----
            price_incidence_evaluation(products_dict_price, product_instance, new_report, products_dict_url)

            #---- INCIDENCIA PRECIO DESCUENTO ----
            special_price_incidence_evaluation(products_dict_special_price, product_instance, new_report, products_dict_url)

        messages.success(request, 'El informe de stock y precios ha sido generado correctamente.')

        return redirect('incidences:falabella_stock_prices_report')


    try:
        products_without_stock = no_stock_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report)
        price_incidences = price_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report)
        special_price_incidences = special_price_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report)
        incidence_groups = product_incidence_group.objects.filter(incidence_report_id=last_incidence_report.id)
        not_existing_products_in_local = existing_product_not_local.objects.filter(incidence_report_id=last_incidence_report.id)

        context = {
            'marketplace_instance': marketplace_instance,
            'last_incidence_report': last_incidence_report,
            'products_without_stock': products_without_stock,
            'price_incidences': price_incidences,
            'special_price_incidences': special_price_incidences,
            'incidence_groups': incidence_groups,
            'not_existing_products_in_local': not_existing_products_in_local,
        }

        return render(request, 'incidences/stock_prices_report.html', context)

    except:
        return render(request, 'incidences/stock_prices_report.html', {'marketplace_instance': marketplace_instance})


def falabella_api_configuration():
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
            'Search': '', #Se convierte el QuerySet en una lista de strings.
            'Filter': 'active'
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

        return response


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


@login_required
def lider_stock_prices_report(request):
    marketplace_instance = marketplace.objects.get(marketplace_name='Lider')
    last_incidence_report = incidence_report.objects.filter(marketplace_id__marketplace_name='Lider', report_type='incorrect prices / no stock').last()

    if request.method == 'POST' and 'export_report' in request.POST:
        #---- La función prices_stock_report_export() se encargará de preparar y exportar el archivo de excel con el informe de incidencias stock y precios. ----
        return prices_stock_report_export(marketplace_instance, last_incidence_report)

    if request.method == 'POST' and 'initiate_report' in request.POST:
        lider_products_queryset = product.objects.filter(marketplace_id__marketplace_name='Lider')

        #---- GET DATA FROM ALL ITEMS FROM API----

        access_token = lider_access_token()

        guid_string = generate_guid()

        headers = {
            'WM_MARKET': 'cl',
            'WM_SEC.ACCESS_TOKEN': access_token,
            'WM_QOS.CORRELATION_ID': guid_string,
            'WM_SVC.NAME': 'Walmart Marketplace',
            'accept': 'application/json'
        }

        params = {
            'limit': '50',
            'nextCursor': '*' #Por defecto, la API de walmart solo entrega hasta 50 productos por consulta. Si se especifíca este parámetro, el response nos dará una variable 'nextCursor' que servira para hacer una nueva consulta para obtener los productos de la "siguiente página" (Los 50 productos que siguen).
        }

        response = requests.get('https://marketplace.walmartapis.com/v3/items?publishedStatus=PUBLISHED', params=params, headers=headers)

        if response.status_code != 200:
            json_to_python_dict  = json.loads(response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
            prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.
            messages.error(request, format_html('Error al intentar obtener productos. Api de walmart dio respuesta: {} <br><br> Respuesta completa: <br> <pre>{}</pre><br>', response.status_code, prettify_json_data)) #Se usa format_html para que el mensaje de error pueda interpretar etiquetas html, como <br> y <pre>. El primer {} representa donde va a ir la variable response.status_code, y el segundo {} representa donde va a ir la variable prettify_json_data. The <pre> tag defines preformatted text. Text in a <pre> element is displayed in a fixed-width font, and the text preserves both spaces and line breaks. The text will be displayed exactly as written in the HTML source code.
            return redirect('incidences:lider_stock_prices_report')

        json_to_python_dict  = json.loads(response.text)
        products_dict = json_to_python_dict["ItemResponse"]

        while True:
            try:
                next_cursor_value = json_to_python_dict['nextCursor']

            except:
                break

            else:
                params['nextCursor'] = next_cursor_value
                
                response = requests.get('https://marketplace.walmartapis.com/v3/items?publishedStatus=PUBLISHED', params=params, headers=headers)

                if response.status_code != 200:
                    json_to_python_dict  = json.loads(response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
                    prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.
                    messages.error(request, format_html('Error al intentar obtener productos. Api de walmart dio respuesta: {} <br><br> Respuesta completa: <br> <pre>{}</pre><br>', response.status_code, prettify_json_data)) #Se usa format_html para que el mensaje de error pueda interpretar etiquetas html, como <br> y <pre>. El primer {} representa donde va a ir la variable response.status_code, y el segundo {} representa donde va a ir la variable prettify_json_data. The <pre> tag defines preformatted text. Text in a <pre> element is displayed in a fixed-width font, and the text preserves both spaces and line breaks. The text will be displayed exactly as written in the HTML source code.
                    return redirect('incidences:lider_stock_prices_report')
                
                json_to_python_dict  = json.loads(response.text)
                products_dict = products_dict + json_to_python_dict["ItemResponse"]

        #---- Llamada a la función que creará un nuebo objeto del model 'incidence_report' ----
        new_report = generate_incidence_report(marketplace_instance, last_incidence_report, 'incorrect prices / no stock', len(products_dict), request)

        for product_item in products_dict:
            product_sku = product_item['sku']
            product_wpid = product_item['wpid']
            product_name = product_item['productName']
            product_shelf = ast.literal_eval(product_item['shelf'])

            try:
                product_category = product_shelf[2]
            except:
                continue

            #La api no entrega la url de un producto, pero si entrega datos para generar esta url.
            product_url = unidecode.unidecode(f"https://www.lider.cl/ip/{product_category.replace(' ', '-').lower()}/{product_name.replace(' ', '-').lower()}/{'0'+ product_item['gtin'][0:len(product_item['gtin'])-1]}")


            #---- VERIFICACIÓN SI EL PRODUCTO EXISTE EN LA BASE DE DATOS LOCAL ----
            if product_sku not in list(lider_products_queryset.values_list('sku', flat=True)):
                existing_product_not_local.objects.create(incidence_report_id=new_report, sku=product_sku, sku_marketplace=product_wpid, product_name=product_name, product_url=product_url)
                continue
            #---- FIN VERIFICACIÓN SI EL PRODUCTO EXISTE EN LA BASE DE DATOS LOCAL ----



            #---- OBTENCIÓN DE PRECIO NORMAL DE WALMART MEDIANTE SCRAPING ----

            #La api de falabella no entrega los dos precios de un producto, por lo que se debe obtener mediante scraping.
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'} 
            # User-Agent --> El User-Agent request header es una cadena característica que le permite a los servidores y servicios de red identificar la aplicación, sistema operativo, compañía, y/o la versión del user agent que hace la petición. La identificación de agente de usuario es uno de los criterios de exclusión utilizado por el estándar de exclusión de robots para impedir el acceso a ciertas secciones de un sitio web, de lo contrario, madaría error 403.

            scraping_response = requests.get(product_url, headers=headers)

            soup = BeautifulSoup(scraping_response.content, "html.parser")

            if scraping_response.status_code != 200: #Por si mediante scraping no se logra acceder al producto del recorrido actual
                not_scrapeable_product.objects.create(product_id=product_instance, incidence_report_id=new_report, http_status_code=scraping_response.status_code)                   
                continue

            try:
                price_value = soup.find('span', class_='strike').text

            except: #Aquí se da a entender que el producto no tiene precio de descuento.
                product_price = int(product_item['price']['amount'])
                product_special_price = None

            else:
                product_price = int(price_value[1:].replace('.',''))
                product_special_price = int(product_item['price']['amount'])


            #---- FIN OBTENCIÓN DE PRECIO NORMAL DE WALMART MEDIANTE SCRAPING ----



            #---- OBTENCIÓN DE STOCK DE WALMART MEDIANTE LLAMADA A API ----
            product_stock_response = get_lider_stock(product_sku, access_token) #Se llama a la función donde se hace una llamada de API para recolectar el stock de cada producto.

            if product_stock_response.status_code != 200:
                json_to_python_dict  = json.loads(product_stock_response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
                prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.
                messages.error(request, format_html('Error al intentar obtener stock del producto {}. Api de walmart dio respuesta: {} <br><br> Respuesta completa: <br> <pre>{}</pre><br>', product_sku, product_stock_response.status_code, prettify_json_data))
                new_report.delete() #Se elimina el reporte que se estaba creando, ya que no se pudo completar exitosamente.
                return redirect('incidences:lider_stock_prices_report')

            else:
                json_to_python_dict = json.loads(product_stock_response.text)
                product_stock = json_to_python_dict['quantity']['amount']

            product_instance = lider_products_queryset.get(sku=product_sku)


            #---- INCIDENCIA STOCK ----
            if product_stock <= 0:
                incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=product_url)

                no_stock_incidence.objects.create(incidence_group_id=incidence_group, stock=product_stock)

            #---- INCIDENCIA PRECIO NORMAL ----
            price_incidence_evaluation(product_price, product_instance, new_report, product_url)


            #---- INCIDENCIA PRECIO DESCUENTO ----
            special_price_incidence_evaluation(product_special_price, product_instance, new_report, product_url)

        messages.success(request, 'El informe de stock y precios ha sido generado correctamente.')

        return redirect('incidences:lider_stock_prices_report')
            
    try:
        products_without_stock = no_stock_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report)
        price_incidences = price_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report)
        special_price_incidences = special_price_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report)
        incidence_groups = product_incidence_group.objects.filter(incidence_report_id=last_incidence_report.id)
        not_scrapeable_products_queryset = not_scrapeable_product.objects.filter(incidence_report_id=last_incidence_report.id)
        not_existing_products_in_local = existing_product_not_local.objects.filter(incidence_report_id=last_incidence_report.id)

        context = {
            'marketplace_instance': marketplace_instance,
            'last_incidence_report': last_incidence_report,
            'products_without_stock': products_without_stock,
            'price_incidences': price_incidences,
            'special_price_incidences': special_price_incidences,
            'incidence_groups': incidence_groups,
            'not_scrapeable_products': not_scrapeable_products_queryset,
            'not_existing_products_in_local': not_existing_products_in_local,
        }

        return render(request, 'incidences/stock_prices_report.html', context)

    except:
        return render(request, 'incidences/stock_prices_report.html', {'marketplace_instance': marketplace_instance})

def lider_access_token():
    #---- CODIFICACIÓN en Base64 del Client ID/Client Secret ---->

    #When you have some binary data that you want to ship across a network, you generally don't do it by just streaming the bits and bytes over the wire in a raw format. Why? because some media are made for streaming text. You never know -- some protocols may interpret your binary data as control characters (like a modem), or your binary data could be screwed up because the underlying protocol might think that you've entered a special character combination (like how FTP translates line endings).

    #So to get around this, people encode the binary data into characters. Base64 is one of these types of encodings.

    # 1. Combine Client ID/Client Secret
    credentials = f"{settings.WALMART_CLIENT_ID}:{settings.WALMART_CLIENT_SECRET}"

    # 2. Encode to bytes (e.g., using UTF-8)
    credentials_bytes = credentials.encode("utf-8")

    # 3. Base64 encode
    encoded_credentials_bytes = base64.b64encode(credentials_bytes)

    # 4. Se pasa de bytes a string
    encoded_credentials_string = encoded_credentials_bytes.decode("utf-8")

    guid_string = generate_guid()

    headers = {
        'Authorization': f"Basic {encoded_credentials_string}",
        'Content-Type': 'application/x-www-form-urlencoded',
        'WM_MARKET': 'cl',
        'WM_SVC.NAME': 'Walmart Marketplace',
        'WM_QOS.CORRELATION_ID': guid_string,
        'accept': 'application/json'
    }

    data = {
        'grant_type': 'client_credentials'
    }

    response = requests.post('https://marketplace.walmartapis.com/v3/token', headers=headers, data=data)

    json_to_python = json.loads(response.text)
    return json_to_python['access_token']

def generate_guid():
    # Generate a new Version 4 UUID
    new_guid = uuid.uuid4() #GUID technically stands for globally unique identifier. What it is, actually, is a 128 bit structure that is unlikely to ever repeat or create a collision, utilizado para identificar de forma única recursos en software y sistemas.

    # Convert the UUID object to a string representation
    guid_string = str(new_guid)

    return guid_string

def get_lider_stock(product_sku, access_token):
    guid_string = generate_guid()

    headers = {
        'WM_MARKET': 'cl',
        'WM_SEC.ACCESS_TOKEN': access_token,
        'WM_QOS.CORRELATION_ID': guid_string,
        'WM_SVC.NAME': 'Walmart Marketplace',
        'accept': 'application/json'
    }

    response = requests.get(f'https://marketplace.walmartapis.com/v3/inventory?sku={product_sku.replace(' ', '%20')}', headers=headers)
    
    return response

def generate_incidence_report(marketplace_instance, last_incidence_report, report_type_str, inspected_products_len, request):
    if last_incidence_report: #Ya existe un reporte de incidencias previo, por lo que se crea uno nuevo con el número de reporte incrementado en 1.
        new_report = incidence_report.objects.create(marketplace_id=marketplace_instance, report_number=last_incidence_report.report_number + 1, report_type=report_type_str, inspected_products=inspected_products_len, created_by=request.user)

    else: #Se crea el primer reporte de incidencias para este contexto.
        new_report = incidence_report.objects.create(marketplace_id=marketplace_instance, report_number=1, report_type=report_type_str, inspected_products=inspected_products_len, created_by=request.user)
    
    return new_report

def price_incidence_evaluation(product_price, product_instance, new_report, product_url):
    if product_price != product_instance.normal_price:

        try:
            incidence_group = product_incidence_group.objects.get(incidence_report_id=new_report, product_id=product_instance)

        except:
            incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=product_url)

            price_incidence.objects.create(incidence_group_id=incidence_group, local_price=product_instance.normal_price, marketplace_price=product_price)

        else:
            price_incidence.objects.create(incidence_group_id=incidence_group, local_price=product_instance.normal_price, marketplace_price=product_price)

def special_price_incidence_evaluation(product_special_price, product_instance, new_report, product_url):
    if product_special_price != product_instance.special_price:

        try:
            incidence_group = product_incidence_group.objects.get(incidence_report_id=new_report, product_id=product_instance)

        except:
            incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=product_url)

            special_price_incidence.objects.create(incidence_group_id=incidence_group, special_local_price=product_instance.special_price, special_marketplace_price=product_special_price)

        else:
            special_price_incidence.objects.create(incidence_group_id=incidence_group, special_local_price=product_instance.special_price, special_marketplace_price=product_special_price)

def prices_stock_report_export(marketplace_instance, last_incidence_report):
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
        response['Content-Disposition'] = f'attachment; filename="{marketplace_instance.marketplace_name.lower()} N°{last_incidence_report.report_number} precio/stock {last_incidence_report.report_date_time.strftime("%Y-%m-%d %H:%M:%S")}.xlsx"'

        return response
