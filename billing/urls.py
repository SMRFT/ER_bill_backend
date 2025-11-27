from django.urls import path,re_path
from . import views

urlpatterns = [
    path('erbilling/', views.er_billing, name='erbilling'),
    path('doctorlist/', views.get_doctor_list, name='doctorlist'),
    path('procedurelist/', views.get_procedure_list, name='procedurelist'),
    path("Pharmacy/", views.get_er_billing),
    re_path(r"^update-status/(?P<uhid>.+)/$", views.update_billing_status),
    path("AccountSummary/", views.get_account_summary),
    path("printbill/", views.printbill),

]
