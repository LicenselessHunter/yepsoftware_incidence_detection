from django.shortcuts import render, redirect
from .models import product, marketplace
from . import resources
from tablib import Dataset #Tablib is an MIT Licensed format-agnostic tabular dataset library, written in Python. It allows you to import, export, and manipulate tabular data sets. Advanced features include, segregation, dynamic columns, tags & filtering, and seamless format import & export. Se combinara con bilbioteca 'django-import-export'
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required #Se importa el decorator.
from . import forms
from django.contrib import messages


@login_required #Ensures that a view can only be accessed by authenticated users. If an unauthenticated user attempts to access a view decorated with @login_required, they will be redirected to the login page.
def products(request, slug):
    marketplace_instance = marketplace.objects.get(slug = slug)
    products = product.objects.filter(marketplace_id=marketplace_instance)

    if request.method == 'POST' and 'export_products_btn' in request.POST:
        product_resource = resources.products_export()
        dataset = product_resource.export(current_marketplace=marketplace_instance.marketplace_name)#El dataset (que representa una agrupación de datos con filas y columnas) se va a igualar a la instancia 'product_resource' con su función de exportación. La biblioteca dejara la variable 'dataset' con la agrupación de datos del model Product y las configuraciones hechas en su resource.
        response = HttpResponse(dataset.xlsx)#Se almacena el dataset en un HttpResponse y se indica con parámetros que será un archivo .xlsx
        response['Content-Disposition'] = f'atachment; filename="productos_{marketplace_instance.marketplace_name.lower()}.xlsx"' #The HTTP Content Disposition is a response-type header field that gives information on how to process the response payload and additional information such as filename when user saves it locally. En este caso, el archivo se llamara 'productos_falabella.xlsx'

        return response #Se retorna el response, el archivo se exporta.



    if request.method == 'POST' and 'import_products_btn' in request.POST:
        product_resource = resources.products_import() #product_resource va a representar el resource 'products_import()'.
        dataset = Dataset()
        new_products = request.FILES['ImportData'] #'request.FILES['ImportData']' Contiene el archivo subido en la pagina para importación.
        dataset.load(new_products.read(),format='xlsx') #Aqui se carga y lee el archivo subido en la página y se especifica su formato.

        result = product_resource.import_data(dataset, dry_run=True, current_user=request.user, current_marketplace=marketplace_instance.marketplace_name) #Se testea el data, se verifica que las propiedades de los campos sean correctos, los formatos, etc. When dry_run is set to True, import_data() will process the dataset and identify the changes that would be made (creations, updates, deletions) but will not actually save them to the database.

        if not result.has_errors(): #Si pasa el testeo.

            result = product_resource.import_data(dataset, dry_run=False, current_user=request.user, current_marketplace=marketplace_instance.marketplace_name)
            '''
            When you are importing a file using import-export, the file is processed row by row. For each row, the import process is going to test whether the row corresponds to an existing stored instance, or whether a new instance is to be created.

            If an existing instance is found, then the instance is going to be updated with the values from the imported row, otherwise a new row will be created.
            '''

            messages.success(request, 'Los productos han sido importados correctamente.')
            return redirect(f'products:products', slug = marketplace_instance.slug)



        elif result.has_errors(): #Si no pasa el testeo, se encontro una excepción o falla (Todo el proceso de importación quedara invalido).

            ErrorDict = {} #Diccionario en donde los keys se dejaran como las líneas del archivo excel y los values como las listas de errores de cada fila. Este es el diccionario que se va a usar en el template para mostrar el informe de errores. Al principio se pensaba en usar los "row_error" en el template, pero no podía manipularlo como quería.

            for line, errors in result.row_errors(): #Se van a recorrer a través de las líneas y errores de "row_errors", el cual contiene los errores especificos de la importación junto a las líneas donde ocurrio.
                for error in errors:
                    ErrorDict[line] = [] #Se va a agregar una lista al diccionario "ErrorDict", con el key representando al line de row_errors()
                    for a in str(error.error).split("--"): #Los errores de line van a ser separados entre si por el simbolo "--"
                        ErrorDict[line].append(a) #Cada error individual de line será agregado a la lista representante del diccionario "ErrorDict"

            context = {
                'ErrorDict':ErrorDict,
                'products':products,
                'result':result,
                'marketplace_instance':marketplace_instance
            }

            return render(request, "products/products.html", context)     

    context = {
        'products': products,
        'marketplace_instance':marketplace_instance
    }
    return render(request, 'products/products.html', context)



@login_required
def product_edit(request, id):
    product_instance = product.objects.get(id = id)
    form = forms.product_edit_form(instance=product_instance)

    if request.method == 'POST' and 'confirm_product_edit' in request.POST:
        form = forms.product_edit_form(request.POST, instance=product_instance)

        if form.is_valid():
            form.save() #Se guarda el registro en la base de datos
            messages.success(request, 'Producto editado correctamente.')

            return redirect(f'products:products', slug = product_instance.marketplace_id.slug)


    if request.method == 'POST' and 'cancel_product_edit' in request.POST:
        return redirect(f'products:products', slug = product_instance.marketplace_id.slug)

    context = {
        'product':product_instance,
        'form':form,
    }

    return render(request, 'products/product_edit.html', context)


@login_required
def product_delete(request, id):
    product_instance = product.objects.get(id = id)

    if request.method == 'POST' and 'confirm_product_delete' in request.POST:
        marketplace_slug = product_instance.marketplace_id.slug

        product_instance.delete()
        messages.success(request, 'Producto eliminado correctamente.')

        return redirect(f'products:products', slug = marketplace_slug)

    if request.method == 'POST' and 'cancel_product_delete' in request.POST:
        return redirect(f'products:products', slug = product_instance.marketplace_id.slug)

    context = {
        'product':product_instance,
    }

    return render(request, 'products/product_delete.html', context)
