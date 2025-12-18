from django.contrib import admin
from .models import incidence_report, product_incidence_group, no_stock_incidence, price_incidence, special_price_incidence, unsellable_incidence, not_scrapeable_product, existing_product_not_local

# Register your models here.
admin.site.register(incidence_report)
admin.site.register(product_incidence_group)
admin.site.register(no_stock_incidence)
admin.site.register(price_incidence)
admin.site.register(special_price_incidence)
admin.site.register(unsellable_incidence)
admin.site.register(not_scrapeable_product)
admin.site.register(existing_product_not_local)