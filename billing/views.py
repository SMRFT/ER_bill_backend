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
    serializer = ERBillingSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Billing saved successfully", "data": serializer.data})
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
@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_er_billing(request):
    date_param = request.GET.get("date")

    # If date is passed → convert to Python date
    if date_param:
        try:
            filter_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"error": "Invalid date format"}, status=400)
    else:
        filter_date = timezone.now().date()  # Today's date

    bills = ERBilling.objects.filter(date=filter_date).order_by("date")
    serializer = ERBillingSerializer(bills, many=True)

    return JsonResponse(serializer.data, safe=False)

@api_view(['PUT'])
@permission_classes([HasRolePermission])
def update_billing_status(request, uhid):
    bill = get_object_or_404(ERBilling, uhid=uhid)
    bill.billing_status = "paid"
    bill.save()
    
    return Response({"message": f"Billing status for UHID {uhid} updated to Billed"})


@api_view(["GET"])
@permission_classes([HasRolePermission])
def get_account_summary(request):
    day = request.GET.get("day")
    month = request.GET.get("month")

    queryset = ERBilling.objects.filter(billing_status="paid")

    # -----------------------------
    # 1️⃣ DAY FILTER (YYYY-MM-DD)
    # -----------------------------
    if day:
        parsed = parse_date(day)
        if parsed:
            start = datetime(parsed.year, parsed.month, parsed.day)
            end = start + timedelta(days=1)

            queryset = queryset.filter(
                date__gte=start,
                date__lt=end
            )

    # -----------------------------
    # 2️⃣ MONTH FILTER (YYYY-MM)
    # -----------------------------
    elif month:
        try:
            year, mon = month.split("-")
            year = int(year)
            mon = int(mon)

            start = datetime(year, mon, 1)

            # calculate next month
            if mon == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, mon + 1, 1)

            queryset = queryset.filter(
                date__gte=start,
                date__lt=end
            )

        except Exception as e:
            return Response({"error": str(e)}, status=400)

    # -----------------------------
    # 3️⃣ DEFAULT → CURRENT MONTH
    # -----------------------------
    else:
        today = datetime.today()

        start = datetime(today.year, today.month, 1)

        # calculate first date of next month
        if today.month == 12:
            end = datetime(today.year + 1, 1, 1)
        else:
            end = datetime(today.year, today.month + 1, 1)

        queryset = queryset.filter(
            date__gte=start,
            date__lt=end
        )

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

    bills = ERBilling.objects.filter(
        billing_status="Billed",
        date__gte=start,
        date__lt=end
    ).order_by("date")

    serializer = ERBillingSerializer(bills, many=True)
    return Response(serializer.data)
