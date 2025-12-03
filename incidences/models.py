from django.db import models
from django.contrib.auth.models import User #Se importa el model User que esta implicito en Django.
from products.models import marketplace, product


# Create your models here.

REPORT_TYPE = (
	('not sellable with stock', 'not sellable with stock'),
	('incorrect prices / no stock', 'incorrect prices / no stock')
)

class incidence_report(models.Model):
    report_number = models.PositiveIntegerField(null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_DEFAULT, default=None, null=True)
    report_date_time = models.DateTimeField(auto_now_add=True)
    marketplace_id = models.ForeignKey(marketplace, on_delete=models.CASCADE)
    inspected_products = models.PositiveIntegerField()
    report_type = models.CharField(max_length=50, choices=REPORT_TYPE, blank=False)


class product_incidence_group(models.Model):
    incidence_report_id = models.ForeignKey(incidence_report, on_delete=models.CASCADE)
    product_id = models.ForeignKey(product, on_delete=models.CASCADE)
    product_url = models.URLField(max_length=200, blank=True, null=True)

class no_stock_incidence(models.Model):
    incidence_group_id = models.ForeignKey(product_incidence_group, on_delete=models.CASCADE)
    stock = models.IntegerField()

class price_incidence(models.Model):
    incidence_group_id = models.ForeignKey(product_incidence_group, on_delete=models.CASCADE)
    local_price = models.PositiveIntegerField()
    marketplace_price = models.PositiveIntegerField()

class special_price_incidence(models.Model):
    incidence_group_id = models.ForeignKey(product_incidence_group, on_delete=models.CASCADE)
    special_local_price = models.PositiveIntegerField(null=True, blank=True)
    special_marketplace_price = models.PositiveIntegerField(null=True, blank=True)

class unsellable_incidence(models.Model):
    incidence_group_id = models.ForeignKey(product_incidence_group, on_delete=models.CASCADE)
    stock = models.IntegerField()

class not_accessible_product(models.Model):
    product_id = models.ForeignKey(product, on_delete=models.CASCADE)
    incidence_report_id = models.ForeignKey(incidence_report, on_delete=models.CASCADE)
    http_status_code = models.PositiveIntegerField()