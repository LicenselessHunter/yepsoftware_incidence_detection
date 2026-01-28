from django.conf import settings
from .models import incidence_report, product_incidence_group, unsellable_incidence, no_stock_incidence, price_incidence, special_price_incidence, not_scrapeable_product, existing_product_not_local
from products.models import product

from selenium import webdriver #import the webdriver module from the selenium library. This import is the foundational step for using Selenium WebDriver in Python to automate web browsers.

    #The webdriver module provides the necessary classes and functions to interact with various web browsers, such as Chrome, Firefox, Edge, Safari, and others.

    #It allows you to create instances of browser drivers (e.g., webdriver.Chrome(), webdriver.Firefox()), which then enable you to control the respective browser programmatically.
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By #‘By’ class is used to specify which attribute is used to locate elements on a page.
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC #Expected Conditions are used with Explicit Waits. Instead of defining the block of code to be executed with a lambda, an expected conditions method can be created to represent common things that get waited on. Some methods take locators as arguments, others take elements as arguments.
from selenium.webdriver.chrome.service import Service

import json #Python has a built-in package called json, which can be used to work with JSON data.
import requests
import urllib.parse
from hashlib import sha256
from hmac import HMAC
from datetime import datetime

from bs4 import BeautifulSoup
import cloudscraper #A simple Python module to bypass Cloudflare's anti-bot page (also known as "I'm Under Attack Mode", or IUAM), implemented with Requests. Cloudflare's anti-bot page currently just checks if the client supports Javascript, though they may add additional techniques in the future.

import base64
import uuid
import ast
import unidecode

import cloudscraper


def falabella_disponibility_report(new_report):
    falabella_products_queryset = product.objects.filter(marketplace_id__marketplace_name='Falabella')

    response = falabella_api_configuration()

    if response.status_code == 200:
        json_to_python_dict = json.loads(response.text) #json.loads() is a function within Python's built-in json module used to deserialize a JSON-formatted string into a Python object. Va a convertir el objeto JSON en un diccionario de python.

    else:
        
        new_report.report_status = 'Failed'
        new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar obtener datos de los productos. Api de falabella dio respuesta: {response.status_code}' #Mensaje de error en formato html para el reporte.

        new_report.save()
        return

    try:
        json_to_python_dict['SuccessResponse']['Body']['Products']['Product']

    except:
        #Por si hay algún error con respecto a la configuración de la API de falabella.

        new_report.report_status = 'Failed'
        falabella_api_error = json_to_python_dict['ErrorResponse']['Head']['ErrorMessage']
        new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> "{falabella_api_error}", consulte a un desarrollador'
        
        new_report.save()
        return

    else:
        products_dict = json_to_python_dict['SuccessResponse']['Body']['Products']['Product']


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
    new_report.report_status = 'Completed'
    new_report.inspected_products = len(products_dict)
    new_report.save()


def falabella_stock_prices_report(new_report):

    falabella_products_queryset = product.objects.filter(marketplace_id__marketplace_name='Falabella')
    response = falabella_api_configuration()

    if response.status_code == 200:
        json_to_python_dict = json.loads(response.text) #json.loads() is a function within Python's built-in json module used to deserialize a JSON-formatted string into a Python object. Va a convertir el objeto JSON en un diccionario de python.

    else:
        new_report.report_status = 'Failed'

        new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar ingresar a Api de falabella. <br> Api dio respuesta: {response.status_code}' #Mensaje de error en formato html para el reporte.

        new_report.save()
        return
    
    try:
        json_to_python_dict['SuccessResponse']['Body']['Products']['Product']

    except:
        #Por si hay algún error con respecto a la configuración de la API de falabella.

        falabella_api_error = json_to_python_dict['ErrorResponse']['Head']['ErrorMessage']
        new_report.report_status = 'Failed'
        new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error en configuración de Api de falabella. <br><br> {falabella_api_error}'
        
        new_report.save()
        return

    else:
        products_dict = json_to_python_dict['SuccessResponse']['Body']['Products']['Product']


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

    new_report.report_status = 'Completed'
    new_report.inspected_products = len(products_dict)
    new_report.save()



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



def lider_stock_prices_report(new_report):
    lider_products_queryset = product.objects.filter(marketplace_id__marketplace_name='Lider')

    #---- GET DATA FROM ALL ITEMS FROM API----

    access_token = lider_access_token()

    guid_string = generate_guid()

    headers = {
        'WM_MARKET': 'cl',
        'WM_SEC.ACCESS_TOKEN': access_token,
        'WM_QOS.CORRELATION_ID': guid_string,
        'WM_SVC.NAME': 'Walmart Marketplace',
        'WM_GLOBAL_VERSION': '3.1',
        'accept': 'application/json'
    }

    params = {
        'limit': '200',
        'nextCursor': '*' #Por defecto, la API de walmart solo entrega hasta 200 productos por consulta. Si se especifíca este parámetro, el response nos dará una variable 'nextCursor' que servira para hacer una nueva consulta para obtener los productos de la "siguiente página" (Los 200 productos que siguen).
    }

    response = requests.get('https://marketplace.walmartapis.com/v3/items?publishedStatus=PUBLISHED', params=params, headers=headers)


    if response.status_code != 200:
        json_to_python_dict  = json.loads(response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
        prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.

        new_report.report_status = 'Failed'

        new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar obtener productos. Api de walmart dio respuesta: {response.status_code} <br><br> <pre>{prettify_json_data}</pre>' #Mensaje de error en formato html para el reporte.

        new_report.save()
        return

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

                new_report.report_status = 'Failed'

                new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar obtener productos. Api de walmart dio respuesta: {response.status_code} <br><br> <pre>{prettify_json_data}</pre>' #Mensaje de error en formato html para el reporte.

                new_report.save()
                return

            json_to_python_dict  = json.loads(response.text)
            products_dict = products_dict + json_to_python_dict["ItemResponse"]  


    #---- CREACIÓN DE INSTANCIA DE CLOUDSCRAPER ----
    scraper = cloudscraper.create_scraper(
        delay=10,
        interpreter='nodejs',
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

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
        

        scraping_response = scraper.get(product_url)
        soup = BeautifulSoup(scraping_response.content, "html.parser")

        if scraping_response.status_code != 200: #Por si mediante scraping no se logra acceder al producto del recorrido actual
            not_scrapeable_product.objects.create(product_id=product_instance, incidence_report_id=new_report, http_status_code=scraping_response.status_code)                   
            continue

        try:
            price_value = soup.find('span', attrs={'data-seo-id': 'strike-through-price'}).text

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
            json_to_python_dict  = json.loads(response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
            prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.

            new_report.report_status = 'Failed'

            new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar obtener stock del producto {product_sku}. Api de walmart dio respuesta: {response.status_code} <br><br> <pre>{prettify_json_data}</pre>' #Mensaje de error en formato html para el reporte.

            new_report.save()
            return

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

    scraper.close()
    new_report.report_status = 'Completed'
    new_report.inspected_products = len(products_dict)
    new_report.save()




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
        'WM_GLOBAL_VERSION': '3.1',
        'accept': 'application/json'
    }

    response = requests.get(f'https://marketplace.walmartapis.com/v3/inventory?sku={product_sku.replace(' ', '%20')}', headers=headers)
    
    return response



def paris_disponibility_report(new_report):

    paris_products_queryset = product.objects.filter(marketplace_id__marketplace_name='Paris')

    #---- SE OBTIENE ACCESS TOKEN DE PARIS MEDIANTE API ----
    response = paris_access_token()


    if response.status_code != 200:
        json_to_python_dict  = json.loads(response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
        prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.

        new_report.report_status = 'Failed'

        new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar obtener el access token. Api de paris dio respuesta: {response.status_code} <br><br> <pre>{prettify_json_data}</pre>' #Mensaje de error en formato html para el reporte.

        new_report.save()
        return


    json_to_python = json.loads(response.text)
    access_token = 'Bearer ' + json_to_python['accessToken']


    #---- SE OBTIENE DATA DE PRODUCTOS DE PARIS MEDIANTE API ----
    url = "https://api-developers.ecomm.cencosud.com/v2/products/search?limit=100&offset=0"

    payload = {}
    headers = {
        'Accept': 'application/json',
        'Authorization': access_token
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    if response.status_code != 200:
        json_to_python_dict  = json.loads(response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
        prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.

        new_report.report_status = 'Failed'

        new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar obtener datos de los productos. Api de paris dio respuesta: {response.status_code} <br><br> <pre>{prettify_json_data}</pre>' #Mensaje de error en formato html para el reporte.

        new_report.save()
        return

    json_to_python = json.loads(response.text)
    products_dict = json_to_python['results']

    actual_product_count = len(json_to_python['results'])
    total_products = json_to_python['total']
    product_page = 1


    while actual_product_count < total_products:

        url = f"https://api-developers.ecomm.cencosud.com/v2/products/search?limit=100&offset={product_page}"

        payload = {}
        headers = {
            'Accept': 'application/json',
            'Authorization': access_token
        }

        response = requests.request("GET", url, headers=headers, data=payload)

        if response.status_code != 200:
            json_to_python_dict  = json.loads(response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
            prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.

            new_report.report_status = 'Failed'

            new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar obtener  datos de los productos. Api de paris dio respuesta: {response.status_code} <br><br> <pre>{prettify_json_data}</pre>' #Mensaje de error en formato html para el reporte.

            new_report.save()
            return

        json_to_python = json.loads(response.text)
        products_dict = products_dict + json_to_python['results']

        actual_product_count += len(json_to_python['results'])
        product_page += 1


    products_dict = {d['id']: d for d in products_dict}


    #---- SE OBTIENE DATA DE STOCK DE PARIS MEDIANTE API ----
    url = "https://api-developers.ecomm.cencosud.com/v2/stock?offset=0&limit=300&withStock=true"

    payload = {}
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': access_token
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    if response.status_code != 200:
        json_to_python_dict  = json.loads(response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
        prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.

        new_report.report_status = 'Failed'

        new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar obtener datos de stock. Api de paris dio respuesta: {response.status_code} <br><br> <pre>{prettify_json_data}</pre>' #Mensaje de error en formato html para el reporte.

        new_report.save()
        return


    json_to_python = json.loads(response.text)
    stock_dict = json_to_python['skus']


    #---- SE PREPARA LA INICIALIZACIÓN DEL WEBDRIVER DE SELENIUM PARA SCRAPING ----

    chrome_options = Options() #Crea una instancia de la clase Options, que se utiliza para configurar opciones específicas para el navegador Chrome cuando se utiliza con Selenium WebDriver.
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--headless=new") #Esto va a evitar que selenium abra la página al correr el script.
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-client-side-phishing-detection")
    chrome_options.add_argument("--disable-oopr-debug-crash-dump")
    chrome_options.add_argument("--no-crash-upload")
    chrome_options.add_argument("--disable-low-res-tiling")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--silent")
    chrome_options.add_argument("--disable-crash-reporter") #prevent the browser from sending crash reports to Google. This can be particularly useful in automated testing environments, especially when running in headless mode, as it can reduce CPU usage and suppress unnecessary log messages. 
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu") 
    chrome_options.add_argument('--disable-dev-shm-usage') #The --disable-dev-shm-usage flag for Chrome/Chromium prevents the browser from using /dev/shm (shared memory) for temporary files, instead directing them to /tmp. It is primarily used in Docker or VM environments where the default shared memory partition is too small, causing crashes or failures. 
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    # Initialize a WebDriver instance (e.g., Chrome. Initializes a new instance of the Chrome web browser for automated testing or web scraping.

    #webdriver: This refers to the webdriver module from the Selenium library, which provides the necessary classes and functions to interact with various web browsers.

    #.Chrome(): This specifically calls the Chrome class within the webdriver module. This class represents the ChromeDriver, a standalone server that implements the W3C WebDriver standard for controlling the Chrome browser.

    #---- FIN DE LA INICIALIZACIÓN DEL WEBDRIVER DE SELENIUM PARA SCRAPING ----


    for product_item in stock_dict:
        marketplace_sku = product_item['sku']
        parent_sku = marketplace_sku.split('-')[0]
        seller_sku = product_item['sku_seller']
        product_name = product_item['title']
        product_stock = product_item['quantity']

        product_url = unidecode.unidecode(f"https://www.paris.cl/{product_name.replace(' ', '-').lower()}-{marketplace_sku}.html")


        #---- VERIFICACIÓN SI EL PRODUCTO EXISTE EN LA BASE DE DATOS LOCAL ----
        if seller_sku not in list(paris_products_queryset.values_list('sku', flat=True)):
            existing_product_not_local.objects.create(incidence_report_id=new_report, sku=seller_sku, sku_marketplace=marketplace_sku, product_name=product_name, product_url=product_url)
            continue
        #---- FIN VERIFICACIÓN SI EL PRODUCTO EXISTE EN LA BASE DE DATOS LOCAL ----

        product_instance = paris_products_queryset.get(sku=seller_sku)

        for variant in products_dict[parent_sku]['publish']['mkp']:
            if variant['variantSku'] == marketplace_sku:

                product_publish_status = variant['publish']

        
        
        if product_publish_status == False:#Este if comprueba que el valor 'publish' para este producto dentro de la API de Paris sea True o False. En caso de que sea False, se concluye que la página de venta de este producto no está disponible para los usuarios, por lo que se crea una incidencia de producto no vendible y se continua al siguiente producto sin necesidad de hacer scraping.
            incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=product_url)
            unsellable_incidence.objects.create(incidence_group_id=incidence_group, stock=product_stock)
            continue




        #---- SCRAPING A PRODUCTO DE PARIS PARA VER SI TIENE BOTÓN DE COMPRA ----

        driver.get(product_url)

        try:
            #Aquí estamos usando un 'explicit wait'. An explicit wait is a code you define to wait for a certain condition to occur before proceeding further in the code. The extreme case of this is time.sleep(), which sets the condition to an exact time period to wait.

            #WebDriverWait is a class in Selenium used to implement explicit waits, which pause code execution until a specific condition is met or a timeout occurs. Aquí estamos diciendo que se pause la ejecución del código hasta que el elemento de la clase 'flex gap-2 flex-col tablet_w:flex-row flex-g' sea encontrada o pasen los 10 de 'timeout' especificado en el segundo parámetro.
            element = WebDriverWait(driver, 100).until(
                EC.presence_of_element_located((By.XPATH, "//*[@class='flex gap-2 flex-col tablet_w:flex-row flex-g']")) #XPath is the language used for locating nodes in an XML document. As HTML can be an implementation of XML (XHTML), Selenium users can leverage this powerful language to target elements in their web applications. En mi caso, lo uso para poder buscar esta "clase compuesta" ya que By.CLASS_NAME no es bueno para buscar clases compuestas.

            )

        except:
            incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=product_url)

            unsellable_incidence.objects.create(incidence_group_id=incidence_group, stock=product_stock)
            continue

    driver.quit() #Finaliza la sesión de WebDriver.
    

    new_report.report_status = 'Completed'
    new_report.inspected_products = len(stock_dict)
    new_report.save()


def paris_stock_prices_report(new_report):

    paris_products_queryset = product.objects.filter(marketplace_id__marketplace_name='Paris')

    #---- SE OBTIENE ACCESS TOKEN DE PARIS MEDIANTE API ----
    response = paris_access_token()

    if response.status_code != 200:
        json_to_python_dict  = json.loads(response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
        prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.

        new_report.report_status = 'Failed'

        new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar obtener el access token. Api de paris dio respuesta: {response.status_code} <br><br> <pre>{prettify_json_data}</pre>' #Mensaje de error en formato html para el reporte.

        new_report.save()
        return


    json_to_python = json.loads(response.text)
    access_token = 'Bearer ' + json_to_python['accessToken']




    #---- SE OBTIENE DATA DE PRODUCTOS DE PARIS MEDIANTE API ----
    url = "https://api-developers.ecomm.cencosud.com/v2/products/search?limit=100&offset=0"

    payload = {}
    headers = {
        'Accept': 'application/json',
        'Authorization': access_token
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    if response.status_code != 200:
        json_to_python_dict  = json.loads(response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
        prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.

        new_report.report_status = 'Failed'

        new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar obtener datos de los productos. Api de paris dio respuesta: {response.status_code} <br><br> <pre>{prettify_json_data}</pre>' #Mensaje de error en formato html para el reporte.

        new_report.save()
        return

    json_to_python = json.loads(response.text)
    products_dict = json_to_python['results']

    actual_product_count = len(json_to_python['results'])
    total_products = json_to_python['total']
    product_page = 1


    while actual_product_count < total_products:

        url = f"https://api-developers.ecomm.cencosud.com/v2/products/search?limit=100&offset={product_page}"

        payload = {}
        headers = {
            'Accept': 'application/json',
            'Authorization': access_token
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code != 200:
            json_to_python_dict  = json.loads(response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
            prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.

            new_report.report_status = 'Failed'

            new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar obtener datos de los productos. Api de paris dio respuesta: {response.status_code} <br><br> <pre>{prettify_json_data}</pre>' #Mensaje de error en formato html para el reporte.

            new_report.save()
            return

        json_to_python = json.loads(response.text)
        products_dict = products_dict + json_to_python['results']

        actual_product_count += len(json_to_python['results'])
        product_page += 1


    products_dict = {d['id']: d for d in products_dict}




    #---- SE OBTIENE DATA DE STOCK DE PARIS MEDIANTE API ----
    url = "https://api-developers.ecomm.cencosud.com/v2/stock?offset=0&limit=300&withStock=false"

    payload = {}
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': access_token
    }

    response = requests.request("GET", url, headers=headers, data=payload)

    if response.status_code != 200:
        json_to_python_dict  = json.loads(response.text) #Se convierte el response de error de api de walmart de un objeto json a un diccionario de python. Luego esto se volverá a convertir en Json pero formateado para que sea más legible en el mensaje de error.
        prettify_json_data = json.dumps(json_to_python_dict, indent=4) #Aquí se convierte el diccionario de python a json pero formateado con 4 identaciones.

        new_report.report_status = 'Failed'

        new_report.error_message = f'<h2>Error del reporte n° {new_report.report_number}</h2> Error al intentar obtener datos de stock. Api de paris dio respuesta: {response.status_code} <br><br> <pre>{prettify_json_data}</pre>' #Mensaje de error en formato html para el reporte.

        new_report.save()
        return

    json_to_python = json.loads(response.text)
    stock_dict = json_to_python['skus']

    for product_item in stock_dict:
        marketplace_sku = product_item['sku']
        parent_sku = marketplace_sku.split('-')[0]
        seller_sku = product_item['sku_seller']
        product_name = product_item['title']
        product_stock = product_item['quantity']


        for variant in products_dict[parent_sku]['variants']:

            if variant['sku'] == marketplace_sku:

                product_special_price = None
                for price in variant['prices']:

                    if price['type']['name'] == 'Precio':
                        product_price = price['value']

                    if price['type']['name'] == 'Precio oferta':
                        product_special_price = price['value']

        product_url = unidecode.unidecode(f"https://www.paris.cl/{product_name.replace(' ', '-').lower()}-{marketplace_sku}.html")

        #---- VERIFICACIÓN SI EL PRODUCTO EXISTE EN LA BASE DE DATOS LOCAL ----
        if seller_sku not in list(paris_products_queryset.values_list('sku', flat=True)):
            existing_product_not_local.objects.create(incidence_report_id=new_report, sku=seller_sku, sku_marketplace=marketplace_sku, product_name=product_name, product_url=product_url)
            continue
        #---- FIN VERIFICACIÓN SI EL PRODUCTO EXISTE EN LA BASE DE DATOS LOCAL ----

        product_instance = paris_products_queryset.get(sku=seller_sku)


        #---- INCIDENCIA STOCK ----
        if product_stock <= 0:
            incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=product_url)

            no_stock_incidence.objects.create(incidence_group_id=incidence_group, stock=product_stock)

        #---- INCIDENCIA PRECIO NORMAL ----
        price_incidence_evaluation(product_price, product_instance, new_report, product_url)


        #---- INCIDENCIA PRECIO DESCUENTO ----
        special_price_incidence_evaluation(product_special_price, product_instance, new_report, product_url)

    new_report.report_status = 'Completed'
    new_report.inspected_products = len(stock_dict)
    new_report.save()


def paris_access_token():
    headers = {
        'Content-Type': 'application/json',
        'Authorization': settings.PARIS_API_KEY
    }

    response = requests.post('https://api-developers.ecomm.cencosud.com/v1/auth/apiKey', headers=headers)

    return response


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