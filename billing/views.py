import os
from bson.json_util import dumps
from django.http import JsonResponse
from .models import ERBilling
from pymongo import MongoClient
from pyauth.auth import HasRolePermission
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from datetime import datetime
from .serializers import ERBillingSerializer
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from rest_framework.response import Response
from django.utils.dateparse import parse_date

@api_view(["POST"])
@permission_classes([HasRolePermission])
def er_billing(request):
    data = request.data

    # Extract employee ID (same as your register API logic)
    employee_id = data.get("auth-user-id")

    serializer = ERBillingSerializer(data=data)

    if serializer.is_valid():
        serializer.save(
            created_by=employee_id,
            created_date=datetime.now()
        )

        return Response({
            "message": "Billing saved successfully",
            "data": serializer.data
        })

    return Response(serializer.errors, status=400)




@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_doctor_list(request):
    mongo_url = os.getenv("GLOBAL_DB_HOST")
    client = MongoClient(mongo_url)
    db = client["ER"]
    collection = db["er_doctors"]

    doctors = list(collection.find({"is_active": True}, {"_id": 0}))
    return JsonResponse(doctors, safe=False)

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_procedure_list(request):
    mongo_url = os.getenv("GLOBAL_DB_HOST")
    client = MongoClient(mongo_url)
    db = client["ER"]
    collection = db["er_procedurelist"]

    procedurelist = list(collection.find({}, {"_id": 0}))
    return JsonResponse(procedurelist, safe=False)

# er_billing/views.py
from datetime import datetime
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import JSONParser
from .models import ERBilling
from .serializers import ERBillingSerializer

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_er_billing(request):
    # Read from query params, not body
    date_str = request.GET.get("date")  # <-- Changed from JSONParser
    
    if not date_str:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
    
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Fetch ALL and filter in Python (MongoDB-safe)
    all_bills = ERBilling.objects.all().order_by("-date")
    
    filtered = []
    for bill in all_bills:
        bill_date = bill.date.date()  # convert Mongo datetime → date only
        if bill_date == selected_date:
            filtered.append(bill)
    
    serializer = ERBillingSerializer(filtered, many=True)
    return JsonResponse(serializer.data, safe=False)


from rest_framework.decorators import api_view, permission_classes,parser_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from rest_framework.parsers import JSONParser

@api_view(['PUT'])
@permission_classes([HasRolePermission])
@parser_classes([JSONParser])
def update_billing_status(request, uhid):
    bill = get_object_or_404(ERBilling, uhid=uhid)

    # Same logic used in ER Register API
    employee_id = request.data.get("auth-user-id")
    print(employee_id)

    # Extract the actual payload under "data"
    payload = request.data.get("data", {})

    payment_mode = payload.get("payment_mode")
    billing_status = payload.get("billing_status")

    if payment_mode is None:
        return Response({"error": "payment_mode is required"}, status=400)

    # Update fields
    bill.payment_mode = payment_mode
    bill.billing_status = billing_status

    # SAME STYLE YOU USED FOR REGISTER
    bill.lastmodified_by = employee_id
    bill.lastmodified_date = datetime.now()

    bill.save()

    return Response({
        "message": "Updated successfully",
        "lastmodified_by": bill.lastmodified_by,
        "lastmodified_date": bill.lastmodified_date
    })

from django.utils import timezone
@api_view(["GET"])
@permission_classes([HasRolePermission])
def get_account_summary(request):
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")
    payment_mode = request.GET.get("payment_mode")

    queryset = ERBilling.objects.filter(billing_status="paid")

    # -----------------------------
    # FROM - TO DATE FILTER
    # -----------------------------
    if from_date and to_date:
        try:
            start = timezone.make_aware(datetime.strptime(from_date, "%Y-%m-%d"))
            end = timezone.make_aware(datetime.strptime(to_date, "%Y-%m-%d")) + timedelta(days=1)

            queryset = queryset.filter(date__gte=start, date__lt=end)

        except Exception as e:
            return Response({"error": f"Invalid date format: {str(e)}"}, status=400)

    # -----------------------------
    # PAYMENT MODE FILTER (FIXED)
    # -----------------------------
    if payment_mode and payment_mode != "all":
        
        # Null payment mode filter
        if payment_mode == "null":
            queryset = queryset.filter(payment_mode__isnull=True)

        else:
            # JSON text match (ex: "[{"method":"upi"}]")
            queryset = queryset.filter(payment_mode__icontains=payment_mode.lower())

    serializer = ERBillingSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([HasRolePermission])
def printbill(request):
    date_param = request.GET.get("date")

    # Use passed date OR today's date
    if date_param:
        try:
            selected = datetime.strptime(date_param, "%Y-%m-%d")
        except ValueError:
            return Response({"error": "Invalid date"}, status=400)
    else:
        selected = timezone.now()

    start = datetime(selected.year, selected.month, selected.day)
    end = start + timedelta(days=1)

    # ❌ Removed billing_status="Billed"
    bills = ERBilling.objects.filter(
        date__gte=start,
        date__lt=end
    ).order_by("date")

    serializer = ERBillingSerializer(bills, many=True)
    return Response(serializer.data)
