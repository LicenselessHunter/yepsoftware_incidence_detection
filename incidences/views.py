from django.shortcuts import render, redirect
from .models import incidence_report, product_incidence_group, unsellable_incidence, no_stock_incidence, price_incidence, special_price_incidence, not_scrapeable_product, existing_product_not_local
from products.models import product, marketplace

from . import resources
from tablib import Dataset #Tablib is an MIT Licensed format-agnostic tabular dataset library, written in Python. It allows you to import, export, and manipulate tabular data sets. Advanced features include, segregation, dynamic columns, tags & filtering, and seamless format import & export. Se combinara con bilbioteca 'django-import-export'
import pandas as pd
from io import BytesIO
from django.contrib import messages
from django.http import HttpResponse


from django.contrib.auth.decorators import login_required #Se importa el decorator. 
from django.db.models import Count

from django_q.tasks import async_task

# Create your views here.
@login_required
def disponibility_report_list(request, slug):
    marketplace_instance = marketplace.objects.get(slug = slug)
    disponibility_reports_query = incidence_report.objects.filter(marketplace_id=marketplace_instance, report_type='not sellable with stock').order_by('-report_date_time')

    context = {
        'marketplace_instance': marketplace_instance,
        'disponibility_reports_query': disponibility_reports_query,
    }

    return render(request, 'incidences/disponibility_report_list.html', context)


@login_required
def stock_prices_report_list(request, slug):
    marketplace_instance = marketplace.objects.get(slug = slug)
    stock_prices_reports_query = incidence_report.objects.filter(marketplace_id=marketplace_instance, report_type='incorrect prices / no stock').order_by('-report_date_time').annotate(
        no_stock_count=Count('product_incidence_group__no_stock_incidence', distinct=True),
        price_incidence_count=Count('product_incidence_group__price_incidence', distinct=True),
        special_price_incidence_count=Count('product_incidence_group__special_price_incidence', distinct=True)
    )
    #The Django **annotate()** method adds a calculated field or a summary value to each object in a QuerySet, directly within a single database query. This allows you to perform complex, per-object analytics efficiently. Para este caso, se están contando las incidencias de stock, precio e incidencia de precio especial asociadas a cada informe de incidencias de precios y stock.

    context = {
        'marketplace_instance': marketplace_instance,
        'stock_prices_reports_query': stock_prices_reports_query,
    }

    return render(request, 'incidences/stock_prices_report_list.html', context)

@login_required
def disponibility_report(request, slug):
    marketplace_instance = marketplace.objects.get(slug = slug)
    last_incidence_report = incidence_report.objects.filter(marketplace_id=marketplace_instance, report_type='not sellable with stock').last()

    last_incidence_report_completed = incidence_report.objects.filter(marketplace_id=marketplace_instance, report_type='not sellable with stock', report_status='Completed').last()

    last_incidence_report_in_progress = incidence_report.objects.filter(marketplace_id=marketplace_instance, report_type='not sellable with stock', report_status='In progress')

    if request.method == 'POST' and 'export_report' in request.POST:
        #---- La función disponibility_report_export() se encargará de preparar y exportar el archivo de excel con el informe de incidencias de disponibilidad. ----
        return disponibility_report_export(marketplace_instance, last_incidence_report)

    if request.method == 'POST' and 'initiate_report' in request.POST:

        #---- Llamada a la función que creará un nuevo objeto del model 'incidence_report' ----
        new_report = generate_incidence_report(marketplace_instance, last_incidence_report, 'not sellable with stock', None, request)

        async_task(f"incidences.async_functions.{marketplace_instance.slug}_disponibility_report", new_report)

        messages.success(request, 'El informe de disponibilidad se ha inicializado correctamente.')
        return redirect('incidences:disponibility_report_list', slug = marketplace_instance.slug)
        


    try:
        not_available_products_queryset = product_incidence_group.objects.filter(incidence_report_id=last_incidence_report_completed.id)
        not_available_products_count = not_available_products_queryset.count()

        not_available_incidences = unsellable_incidence.objects.filter(incidence_group_id__in=not_available_products_queryset)
        incidence_groups = product_incidence_group.objects.filter(incidence_report_id=last_incidence_report_completed.id)
        not_scrapeable_products_queryset = not_scrapeable_product.objects.filter(incidence_report_id=last_incidence_report_completed.id)
        not_existing_products_in_local = existing_product_not_local.objects.filter(incidence_report_id=last_incidence_report_completed.id)

        context = {
            'last_incidence_report_in_progress': last_incidence_report_in_progress,
            'marketplace_instance': marketplace_instance,
            'last_incidence_report_completed': last_incidence_report_completed,
            'not_available_products_count': not_available_products_count,
            'not_available_incidences': not_available_incidences,
            'not_scrapeable_products': not_scrapeable_products_queryset,
            'incidence_groups': incidence_groups,
            'not_existing_products_in_local': not_existing_products_in_local,
        }

        return render(request, 'incidences/disponibility_report.html', context)

    except:

        context = {
            'last_incidence_report_in_progress': last_incidence_report_in_progress,
            'marketplace_instance': marketplace_instance
        }

        return render(request, 'incidences/disponibility_report.html', context)

@login_required
def stock_prices_report(request, slug):
    marketplace_instance = marketplace.objects.get(slug = slug)

    last_incidence_report = incidence_report.objects.filter(marketplace_id=marketplace_instance, report_type='incorrect prices / no stock').last()

    last_incidence_report_completed = incidence_report.objects.filter(marketplace_id=marketplace_instance, report_type='incorrect prices / no stock', report_status='Completed').last()

    last_incidence_report_in_progress = incidence_report.objects.filter(marketplace_id=marketplace_instance, report_type='incorrect prices / no stock', report_status='In progress')


    if request.method == 'POST' and 'export_report' in request.POST:
        #---- La función prices_stock_report_export() se encargará de preparar y exportar el archivo de excel con el informe de incidencias stock y precios. ----
        return prices_stock_report_export(marketplace_instance, last_incidence_report)

    if request.method == 'POST' and 'initiate_report' in request.POST:

        new_report = generate_incidence_report(marketplace_instance, last_incidence_report, 'incorrect prices / no stock', None, request)

        async_task(f"incidences.async_functions.{marketplace_instance.slug}_stock_prices_report", new_report)
        messages.success(request, 'El informe de precios y stock se ha inicializado correctamente.')
        return redirect('incidences:stock_prices_report_list', slug = marketplace_instance.slug)

    try:
        products_without_stock = no_stock_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report_completed)
        price_incidences = price_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report_completed)
        special_price_incidences = special_price_incidence.objects.filter(incidence_group_id__incidence_report_id=last_incidence_report_completed)
        incidence_groups = product_incidence_group.objects.filter(incidence_report_id=last_incidence_report_completed.id)
        not_scrapeable_products_queryset = not_scrapeable_product.objects.filter(incidence_report_id=last_incidence_report_completed.id)
        not_existing_products_in_local = existing_product_not_local.objects.filter(incidence_report_id=last_incidence_report_completed.id)

        context = {
            'last_incidence_report_in_progress': last_incidence_report_in_progress,
            'marketplace_instance': marketplace_instance,
            'last_incidence_report_completed': last_incidence_report_completed,
            'products_without_stock': products_without_stock,
            'price_incidences': price_incidences,
            'special_price_incidences': special_price_incidences,
            'incidence_groups': incidence_groups,
            'not_scrapeable_products': not_scrapeable_products_queryset,
            'not_existing_products_in_local': not_existing_products_in_local,
        }

        return render(request, 'incidences/stock_prices_report.html', context)

    except:

        context = {
            'last_incidence_report_in_progress': last_incidence_report_in_progress,
            'marketplace_instance': marketplace_instance
        }

        return render(request, 'incidences/stock_prices_report.html', context)


def generate_incidence_report(marketplace_instance, last_incidence_report, report_type_str, inspected_products_len, request):
    if last_incidence_report: #Ya existe un reporte de incidencias previo, por lo que se crea uno nuevo con el número de reporte incrementado en 1.
        new_report = incidence_report.objects.create(marketplace_id=marketplace_instance, report_number=last_incidence_report.report_number + 1, report_type=report_type_str, inspected_products=inspected_products_len, created_by=request.user, report_status='In progress')

    else: #Se crea el primer reporte de incidencias para este contexto.
        new_report = incidence_report.objects.create(marketplace_id=marketplace_instance, report_number=1, report_type=report_type_str, inspected_products=inspected_products_len, created_by=request.user, report_status='In progress')
    
    return new_report


def disponibility_report_export(marketplace_instance, last_incidence_report):
    disponibility_report_resource = resources.disponibility_report_export()
    dataset = disponibility_report_resource.export(current_report=last_incidence_report)

    response = HttpResponse(dataset.xlsx)
    response['Content-Disposition'] = f'attachment; filename="{marketplace_instance.marketplace_name.lower()} N°{last_incidence_report.report_number} disponibilidad {last_incidence_report.report_date_time.strftime("%Y-%m-%d %H:%M:%S")}.xlsx"' #An f-string allows you to embed Python expressions directly inside string literals by enclosing them in curly braces {}. When the code is executed, Python replaces the expressions inside the braces with their resulting values. Aquí se usa para insertar variables dentro del string que define el nombre del archivo exportado.

    #The strftime() method in Python is used to format datetime or time objects into a string representation based on a specified format. The name "strftime" stands for "string format time." This method is part of the datetime module and is commonly used for converting date and time information into a human-readable and customizable string.

    return response

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
