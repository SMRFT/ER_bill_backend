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
    path("er_report/", views.er_report),
    path("get_next_bill_number/", views.get_next_bill_number),
    # re_path(r"^erreport/$", views.er_report),
]
