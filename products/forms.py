from django import forms #Se está importando la creación de forms de django para que podamos crear nuestro propio model form.
from . import models #Desde "."(directorio actual) se va a importar "models.py"

class product_edit_form(forms.ModelForm): #Esta clase va a representar el producto, va a heredar de "forms.ModelForm"
	class Meta: #Esta clase va a contener los campos o elementos que queremos mostrar en el form.
		model = models.product #El model que vamos a usar, va a ser igual a la clase Producto de "models.py"
		fields = ['product_name', 'normal_price', 'special_price'] 

		labels = {
			'product_name':'Nombre del producto',
			'normal_price':'Precio',
			'special_price':'Precio de descuento',
		}
