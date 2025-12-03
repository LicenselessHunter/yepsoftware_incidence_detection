from import_export import resources, fields
from . import models #Desde "."(directorio actual) se va a importar "models.py"

class products_export(resources.ModelResource):

	#Override to filter an export queryset.
	def filter_export(self, queryset, *args, **kwargs):
		# Example: Filter books published after a certain date
		# You might pass the date as a kwarg from your admin or view

		queryset = queryset.filter(marketplace_id__marketplace_name=kwargs['current_marketplace'])
		return queryset



	#Aquí estamos declarando nombres personalizados para los headers del archivo excel. Por ejemplo, en la variable 'product_name_header', usamos el parámetro 'attribute' para referenciar el campo del model y el parámetro 'column_name' lo usamos para definir el nombre del header personalizado que aparecera en el archivo excel.
	product_name_header = fields.Field(attribute='product_name', column_name='nombre')
	normal_price_header = fields.Field(attribute='normal_price', column_name='precio')
	special_price_header = fields.Field(attribute='special_price', column_name='precio_descuento')


	class Meta:
		model = models.product
		#You can optionally use the fields declaration to affect which fields are handled during import / export
		fields = ('sku', 'sku_marketplace', 'product_name_header', 'normal_price_header', 'special_price_header',)



class products_import(resources.ModelResource):

	def before_import_row(self, row, **kwargs): #Función de la misma biblioteca que se utiliza para realizar alguna acción antes de importar un row del archivo subido.
		row['marketplace_id'] = models.marketplace.objects.get(marketplace_name=kwargs['current_marketplace']).id
		row['created_by'] = kwargs['current_user'].id

		errors = [] #Lista que contendra los errores de cada fila


		#LEVANTAMIENTO DE ERROR CAMPO "SKU"
		if isinstance(row['sku'], str):
			if len(row['sku']) == 0 or len(row['sku']) > 30:
				errors.append(str(Exception("sku debe tener entre 1 a 30 caracteres")))

			elif models.product.objects.filter(sku = row['sku'], marketplace_id__marketplace_name=kwargs['current_marketplace']).exists():
				errors.append(str(Exception("sku de " + kwargs['current_marketplace'] + " ya existente en la aplicación o en alguna línea anterior sin error del archivo de importación")))

		else:
			errors.append(str(Exception("sku debe ser un campo de texto")))


		#LEVANTAMIENTO DE ERROR CAMPO "SKU_marketplace"
		if isinstance(row['sku_marketplace'], str):
			if len(row['sku_marketplace']) == 0 or len(row['sku_marketplace']) > 30:
				errors.append(str(Exception("sku_marketplace debe tener entre 1 a 30 caracteres")))

			elif models.product.objects.filter(sku_marketplace = row['sku_marketplace'], marketplace_id__marketplace_name=kwargs['current_marketplace']).exists():
				errors.append(str(Exception("sku_marketplace de " + kwargs['current_marketplace'] + " ya existente en la aplicación o en alguna línea anterior sin error del archivo de importación")))

		else:
			errors.append(str(Exception("sku_marketplace debe ser un campo de texto")))


		#LEVANTAMIENTO DE ERROR CAMPO "nombre"
		if isinstance(row['nombre'], str):
			if len(row['nombre']) == 0 or len(row['nombre']) > 100:
				errors.append(str(Exception("nombre debe tener entre 1 a 100 caracteres")))

		else:
			errors.append(str(Exception("nombre debe ser un campo de texto")))



		#LEVANTAMIENTO DE ERROR CAMPO "precio"
		try:
			price_row = float(row['precio']) #Un string "3" se convertirá en valor 3.0
			if price_row <= 0 or price_row.is_integer() == False:
				#.is_integer()
					#It returns True if the float value is numerically equivalent to an integer (e.g., 5.0, 10.0).
					#It returns False if the float value has a non-zero fractional part (e.g., 5.5, 10.1).

				errors.append(str(Exception("precio debe ser un número entero positivo")))
			#int(row['precio'])

		except: #En caso de que row['precio'] sea un string que no se pueda convertir en float o un campo vacío.
			errors.append(str(Exception("precio debe ser un número entero positivo")))

		else:
		    row['precio'] = int(float(row['precio']))



        #LEVANTAMIENTO DE ERROR CAMPO "precio_descuento"
		try:
			special_price_row = float(row['precio_descuento']) #Un string "3" se convertirá en valor 3.0
			if special_price_row < 0 or special_price_row.is_integer() == False:
				#.is_integer()
					#It returns True if the float value is numerically equivalent to an integer (e.g., 5.0, 10.0).
					#It returns False if the float value has a non-zero fractional part (e.g., 5.5, 10.1).

				errors.append(str(Exception("precio de descuento debe ser un número igual o mayor a 0 o un campo vacío")))
			#int(row['precio'])

		except: #En caso de que row['precio_descuento'] sea un string que no se pueda convertir en float o un campo vacío.
			if row['precio_descuento'] is not None and row['precio_descuento'] != '':
				errors.append(str(Exception("precio de descuento debe ser un número igual o mayor a 0 o un campo vacío")))

			else:
			    row['precio_descuento'] = None

		else:
		    row['precio_descuento'] = int(float(row['precio_descuento']))




		#SI ES QUE LA LISTA "errors" TIENE CONTENIDO
		if errors:
			errors = "--".join(errors) #Se usa este join para sacar los [] de la lista de errores de esta fila, además entre cada error de la fila se agregara el signo "--" para que después en views.py se puedan separar correctamente, puede ser cualquier signo enrealidad.

			raise Exception(errors)



	#Aquí estamos declarando nombres personalizados para los headers del archivo excel. Por ejemplo, en la variable 'product_name_header', usamos el parámetro 'attribute' para referenciar el campo del model y el parámetro 'column_name' lo usamos para definir el nombre del header personalizado que aparecera en el archivo excel.
	product_name_header = fields.Field(attribute='product_name', column_name='nombre')
	normal_price_header = fields.Field(attribute='normal_price', column_name='precio')
	special_price_header = fields.Field(attribute='special_price', column_name='precio_descuento')


	class Meta:
		model = models.product