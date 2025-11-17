from import_export import resources, fields
from . import models #Desde "."(directorio actual) se va a importar "models.py"

class disponibility_report_export(resources.ModelResource):

	#Override to filter an export queryset.
	def filter_export(self, queryset, *args, **kwargs):
		queryset = queryset.filter(incidence_group_id__incidence_report_id=kwargs['current_report'])
		return queryset

	sku_header = fields.Field(attribute='incidence_group_id__product_id__sku', column_name='sku')
	sku_marketplace_header = fields.Field(attribute='incidence_group_id__product_id__sku_marketplace', column_name='sku marketplace')
	product_name_header = fields.Field(attribute='incidence_group_id__product_id__product_name', column_name='nombre producto')
	product_url_header = fields.Field(attribute='incidence_group_id__product_url', column_name='url producto')
	
	description_field = fields.Field(column_name='Descripción incidencia') #Campo personalizado que no existe en el model, se crea para agregar una descripción de la incidencia en el archivo exportado.

	class Meta:
		model = models.unsellable_incidence
		fields = ('sku_header', 'sku_marketplace_header', 'product_name_header', 'description_field', 'stock', 'product_url_header',)
    
	def dehydrate_description_field(self, unsellable_incidence): #Función que se utiliza para definir el valor del campo personalizado 'description_field' en el archivo exportado.

        # This method is called for each object during export
        # You can perform any logic here to generate the custom field's value
		return "Este producto no se puede comprar, a pesar de tener stock."




class stock_prices_report_export(resources.ModelResource):

	#Override to filter an export queryset.
	def filter_export(self, queryset, *args, **kwargs):
		queryset = queryset.filter(incidence_group_id__incidence_report_id=kwargs['current_report'])
		return queryset

	sku_header = fields.Field(attribute='incidence_group_id__product_id__sku', column_name='sku')
	sku_marketplace_header = fields.Field(attribute='incidence_group_id__product_id__sku_marketplace', column_name='sku marketplace')
	product_name_header = fields.Field(attribute='incidence_group_id__product_id__product_name', column_name='nombre producto')
	product_url_header = fields.Field(attribute='incidence_group_id__product_url', column_name='url producto')

	description_field = fields.Field(column_name='Descripción incidencia') #Campo personalizado que no existe en el model, se crea para agregar una descripción de la incidencia en el archivo exportado.
	
	class Meta:
		model = models.no_stock_incidence
		fields = ('sku_header', 'sku_marketplace_header', 'product_name_header', 'description_field', 'stock', 'product_url_header',)
		
	def dehydrate_description_field(self, no_stock_incidence): #Función que se utiliza para definir el valor del campo personalizado 'description_field' en el archivo exportado.

        # This method is called for each object during export
        # You can perform any logic here to generate the custom field's value
		return "Producto sin stock en el marketplace."



class normal_prices_report_export(resources.ModelResource):

	#Override to filter an export queryset.
	def filter_export(self, queryset, *args, **kwargs):
		queryset = queryset.filter(incidence_group_id__incidence_report_id=kwargs['current_report'])
		return queryset

	sku_header = fields.Field(attribute='incidence_group_id__product_id__sku', column_name='sku')
	sku_marketplace_header = fields.Field(attribute='incidence_group_id__product_id__sku_marketplace', column_name='sku marketplace')
	product_name_header = fields.Field(attribute='incidence_group_id__product_id__product_name', column_name='nombre producto')
	product_url_header = fields.Field(attribute='incidence_group_id__product_url', column_name='url producto')
	local_price_header = fields.Field(attribute='local_price', column_name='precio aplicación')
	marketplace_price_header = fields.Field(attribute='marketplace_price', column_name='precio marketplace')

	description_field = fields.Field(column_name='Descripción incidencia') #Campo personalizado que no existe en el model, se crea para agregar una descripción de la incidencia en el archivo exportado.

	class Meta:
		model = models.price_incidence
		fields = ('sku_header', 'sku_marketplace_header', 'product_name_header', 'description_field', 'local_price_header', 'marketplace_price_header', 'product_url_header',)

	def dehydrate_description_field(self, price_incidence): #Función que se utiliza para definir el valor del campo personalizado 'description_field' en el archivo exportado.

        # This method is called for each object during export
        # You can perform any logic here to generate the custom field's value
		return "Precios diferentes entre esta aplicación y el marketplace."


class special_prices_report_export(resources.ModelResource):

	#Override to filter an export queryset.
	def filter_export(self, queryset, *args, **kwargs):
		queryset = queryset.filter(incidence_group_id__incidence_report_id=kwargs['current_report'])
		return queryset

	sku_header = fields.Field(attribute='incidence_group_id__product_id__sku', column_name='sku')
	sku_marketplace_header = fields.Field(attribute='incidence_group_id__product_id__sku_marketplace', column_name='sku marketplace')
	product_name_header = fields.Field(attribute='incidence_group_id__product_id__product_name', column_name='nombre producto')
	product_url_header = fields.Field(attribute='incidence_group_id__product_url', column_name='url producto')
	local_special_price_header = fields.Field(attribute='special_local_price', column_name='precio descuento aplicación')
	marketplace_special_price_header = fields.Field(attribute='special_marketplace_price', column_name='precio descuento marketplace')

	description_field = fields.Field(column_name='Descripción incidencia') #Campo personalizado que no existe en el model, se crea para agregar una descripción de la incidencia en el archivo exportado.

	class Meta:
		model = models.special_price_incidence
		fields = ('sku_header', 'sku_marketplace_header', 'product_name_header', 'description_field', 'local_special_price_header', 'marketplace_special_price_header', 'product_url_header',)

	def dehydrate_description_field(self, special_price_incidence): #Función que se utiliza para definir el valor del campo personalizado 'description_field' en el archivo exportado.

        # This method is called for each object during export
        # You can perform any logic here to generate the custom field's value
		return "Precios de descuento diferentes entre esta aplicación y el marketplace."