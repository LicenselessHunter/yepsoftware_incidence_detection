from django.conf import settings
import json #Python has a built-in package called json, which can be used to work with JSON data.
from .models import incidence_report, product_incidence_group, unsellable_incidence, no_stock_incidence, price_incidence, special_price_incidence, existing_product_not_local
from products.models import product

from selenium import webdriver #import the webdriver module from the selenium library. This import is the foundational step for using Selenium WebDriver in Python to automate web browsers.

    #The webdriver module provides the necessary classes and functions to interact with various web browsers, such as Chrome, Firefox, Edge, Safari, and others.

    #It allows you to create instances of browser drivers (e.g., webdriver.Chrome(), webdriver.Firefox()), which then enable you to control the respective browser programmatically.
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By #‘By’ class is used to specify which attribute is used to locate elements on a page.
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC #Expected Conditions are used with Explicit Waits. Instead of defining the block of code to be executed with a lambda, an expected conditions method can be created to represent common things that get waited on. Some methods take locators as arguments, others take elements as arguments.

import unidecode
import requests

from django.utils.html import format_html

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



    for product_item in stock_dict:
        marketplace_sku = product_item['sku']
        parent_sku = marketplace_sku[0:-2]
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


        if product_publish_status == False:
            incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=product_url)
            unsellable_incidence.objects.create(incidence_group_id=incidence_group, stock=product_stock)
            continue




        #---- SCRAPING A PRODUCTO DE PARIS PARA VER SI TIENE BOTÓN DE COMPRA ----
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--headless") #Esto va a evitar que selenium abra la página al correr el script.
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36")


        driver = webdriver.Chrome(options=chrome_options)# Initialize a WebDriver instance (e.g., Chrome. Initializes a new instance of the Chrome web browser for automated testing or web scraping.

        #webdriver: This refers to the webdriver module from the Selenium library, which provides the necessary classes and functions to interact with various web browsers.

        #.Chrome(): This specifically calls the Chrome class within the webdriver module. This class represents the ChromeDriver, a standalone server that implements the W3C WebDriver standard for controlling the Chrome browser.

        driver.get(product_url)

        try:
            #Aquí estamos usando un 'explicit wait'. An explicit wait is a code you define to wait for a certain condition to occur before proceeding further in the code. The extreme case of this is time.sleep(), which sets the condition to an exact time period to wait.

            #WebDriverWait is a class in Selenium used to implement explicit waits, which pause code execution until a specific condition is met or a timeout occurs. Aquí estamos diciendo que se pause la ejecución del código hasta que el elemento de la clase 'flex gap-2 flex-col tablet_w:flex-row flex-g' sea encontrada o pasen los 10 de 'timeout' especificado en el segundo parámetro.
            element = WebDriverWait(driver, 100).until(
                EC.presence_of_element_located((By.XPATH, "//*[@class='flex gap-2 flex-col tablet_w:flex-row flex-g']")) #XPath is the language used for locating nodes in an XML document. As HTML can be an implementation of XML (XHTML), Selenium users can leverage this powerful language to target elements in their web applications. En mi caso, lo uso para poder buscar esta "clase compuesta" ya que By.CLASS_NAME no es bueno para buscar clases compuestas.
                
            )

        except:
            driver.quit()
            incidence_group = product_incidence_group.objects.create(incidence_report_id=new_report, product_id=product_instance, product_url=product_url)

            unsellable_incidence.objects.create(incidence_group_id=incidence_group, stock=product_stock)
            continue

        driver.quit()

    
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
