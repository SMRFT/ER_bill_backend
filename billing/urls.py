from django.urls import path,re_path
from . import views

urlpatterns = [
    path('erbilling/', views.er_billing, name='erbilling'),
    path('doctorlist/', views.get_doctor_list, name='doctorlist'),
    path('procedurelist/', views.get_procedure_list, name='procedurelist'),
    path("Pharmacy/", views.get_er_billing),
    re_path(r"^update-status/(?P<billnumber>.+)/$", views.update_billing_status),
    path("AccountSummary/", views.get_shift_account_summary),
    path("printbill/", views.printbill),
    path("er_report/", views.er_report),
    path("get_next_bill_number/", views.get_next_bill_number),
    path("shiftdetails/", views.post_shiftdetails),
    path("get_active_shift/", views.get_active_shift),
    path("get_pharmacist_shiftreport/", views.get_pharmacist_shiftreport),
    path("View_bills_report/", views.View_bills_report),
    path("View_bills_discount_report/", views.View_bills_discount_report),

    path("get_billing_for_discount/", views.get_billing_for_discount),
    path("update_billing_discount/", views.update_billing_discount),
    path("soft_delete_billing/", views.soft_delete_billing),
]
