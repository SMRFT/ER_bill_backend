import os
from bson.json_util import dumps
from django.http import JsonResponse
from .models import ERBilling,Shiftdetails
from pymongo import MongoClient
from pyauth.auth import HasRolePermission
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone
from datetime import datetime
from .serializers import ERBillingSerializer,ShiftdetailsSerializer
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta
from rest_framework.response import Response
from django.utils.dateparse import parse_date

@api_view(["POST"])
@permission_classes([HasRolePermission])
def er_billing(request):
    data = request.data
    employee_id = data.get("auth-user-id")

    # Auto generate billnumber here
    current_year = datetime.now().year % 100
    next_year = (datetime.now().year + 1) % 100
    prefix = f"{current_year:02d}{next_year:02d}"

    latest = (
        ERBilling.objects.filter(billnumber__startswith=prefix)
        .order_by("-billnumber")
        .first()
    )

    if latest:
        try:
            last_num = int(latest.billnumber.split("/")[-1])
        except:
            last_num = 0
    else:
        last_num = 0

    new_billnumber = f"{prefix}/{last_num + 1:02d}"

    serializer = ERBillingSerializer(data=data)

    if serializer.is_valid():
        serializer.save(
            billnumber=new_billnumber,
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
    db = client["ER_Billing"]
    collection = db["doctors_list"]

    doctors = list(collection.find({"is_active": True}, {"_id": 0}))
    return JsonResponse(doctors, safe=False)

@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_procedure_list(request):
    mongo_url = os.getenv("GLOBAL_DB_HOST")
    client = MongoClient(mongo_url)
    db = client["ER_Billing"]
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
def update_billing_status(request, billnumber):
    bill = get_object_or_404(ERBilling, billnumber=billnumber)

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

import os
import json
from pymongo import MongoClient
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes



@api_view(["GET"])
@permission_classes([HasRolePermission])
def get_shift_account_summary(request):
    mongo_url = os.getenv("GLOBAL_DB_HOST")
    client = MongoClient(mongo_url)

    er_db = client["ER_Billing"]
    shift_collection = er_db["er_shiftdetails"]
    billing_collection = er_db["billing_erbilling"]

    global_db = client["Global"]
    profile_collection = global_db["backend_diagnostics_profile"]

    from_date = request.GET.get("from")
    to_date = request.GET.get("to")

    date_filter = {}
    if from_date and to_date:
        start_day = datetime.strptime(from_date, "%Y-%m-%d")
        end_day = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        date_filter = {"starttime": {"$gte": start_day, "$lte": end_day}}

    shifts = list(shift_collection.find({**date_filter, "is_active": False}).sort("starttime", -1))

    response_data = []

    for shift in shifts:
        employee_id = str(shift.get("created_by"))

        # ✅ Employee lookup safe
        profile = profile_collection.find_one({
            "$or": [
                {"employeeId": employee_id},
                {"employeeId": int(employee_id) if employee_id.isdigit() else employee_id}
            ]
        })

        employee_name = profile.get("employeeName") if profile else "Unknown"

        start = shift.get("starttime")
        end = shift.get("endtime")

        if not start:
            continue

        # ✅ BILL FILTER BY DATE ONLY (NOT seconds)
        day_start = start.replace(hour=0, minute=0, second=0)
        day_end = start.replace(hour=23, minute=59, second=59)

        bills = list(billing_collection.find({
            "billing_status": "paid",
            "lastmodified_by": {"$in": [employee_id, int(employee_id) if employee_id.isdigit() else employee_id]},
            "lastmodified_date": {"$gte": day_start, "$lte": day_end}
        }))

        total_amount = 0
        cash_total = 0
        digital_total = 0   # Card + UPI

        patient_details = []

        for bill in bills:
            bill_total = 0
            payment_modes = []

            modes = bill.get("payment_mode", [])
            if isinstance(modes, str):
                modes = json.loads(modes)

            for m in modes:
                amt = float(m.get("amount", 0))
                method = m.get("method", "").lower()

                bill_total += amt

                if method == "cash":
                    cash_total += amt
                elif method in ["upi", "card"]:
                    digital_total += amt
                else:
                    digital_total += amt  # treat other modes as digital

                payment_modes.append({"method": method, "amount": amt})


            total_amount += bill_total

            procedures = bill.get("procedures", [])
            if isinstance(procedures, str):
                procedures = json.loads(procedures)

            patient_details.append({
                "patientname": bill.get("patientname"),
                "uhid": bill.get("uhid"),
                "procedures": procedures,
                "payments": payment_modes,
                "total": bill_total
            })

        response_data.append({
            "shiftno": shift.get("shiftno"),
            "employee_name": employee_name,
            "starttime": start,
            "endtime": end,
            "cash_total": cash_total,
            "digital_total": digital_total,
            "total_amount": total_amount,
            "patients": patient_details
        })

    return JsonResponse({"success": True, "data": response_data}, safe=False)



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




@api_view(['GET'])
@permission_classes([HasRolePermission])
def get_next_bill_number(request):
    current_year = datetime.now().year % 100
    next_year = (datetime.now().year + 1) % 100
    prefix = f"{current_year:02d}{next_year:02d}"

    # Get latest bill with prefix → order by number
    latest_bill = (
        ERBilling.objects.filter(billnumber__startswith=prefix)
        .order_by("-billnumber")
        .first()
    )

    if latest_bill:
        try:
            last_num = int(latest_bill.billnumber.split("/")[-1])
        except:
            last_num = 0
    else:
        last_num = 0

    next_number = last_num + 1
    next_bill = f"{prefix}/{next_number:02d}"

    return Response({"billNumber": next_bill})





from rest_framework.decorators import api_view
from rest_framework.response import Response
from datetime import datetime
from .models import ERBilling
from .serializers import ERBillingSerializer


@api_view(["POST"])
@permission_classes([HasRolePermission])
def er_report(request):
    try:
        # ✅ Read from payload
        from_date = request.data.get("from_date")
        to_date = request.data.get("to_date")

        if not from_date or not to_date:
            return Response({
                "success": False,
                "message": "from_date and to_date are required"
            }, status=400)

        # ✅ Payload format: YYYY-MM-DD
        start_date = datetime.strptime(from_date, "%Y-%m-%d")
        end_date = datetime.strptime(to_date, "%Y-%m-%d")
        end_date = end_date.replace(hour=23, minute=59, second=59)

        queryset = ERBilling.objects.filter(
            date__range=(start_date, end_date)
        ).order_by("-date")

        serializer = ERBillingSerializer(queryset, many=True)

        male = 0
        female = 0
        patients = []

        for item in serializer.data:
            gender = (item.get("gender") or "").lower()

            if gender == "male":
                male += 1
            elif gender == "female":
                female += 1

            patients.append({
                "date": datetime.fromisoformat(item["date"]).strftime("%d-%m-%Y"),
                "billnumber": item["billnumber"],
                "uhid": item["uhid"],
                "patientname": item["patientname"],
                "gender": item["gender"],
                "doctorname": item["doctorname"],
                "total": item["total"],
                "net_amount": item["net_amount"],
            })

        return Response({
            "success": True,
            "summary": {
                "male": male,
                "female": female,
                "total": queryset.count()
            },
            "patients": patients
        })

    except Exception as e:
        return Response({
            "success": False,
            "error": str(e)
        }, status=500)
    



from datetime import datetime
from pymongo import MongoClient, DESCENDING
import os
import re

def generate_shift_number():
    now = datetime.now()

    # 🔹 Financial year logic (Apr–Mar)
    if now.month >= 4:
        start_year = now.year % 100
        end_year = (now.year + 1) % 100
    else:
        start_year = (now.year - 1) % 100
        end_year = now.year % 100

    prefix = f"{start_year:02d}{end_year:02d}"  # Example: 2526

    mongo_url = os.getenv("GLOBAL_DB_HOST")
    client = MongoClient(mongo_url)
    db = client["ER_Billing"]
    collection = db["er_shiftdetails"]

    # 🔹 Find last shift of THIS financial year only
    last_shift = collection.find_one(
        {"shiftno": {"$regex": f"^{prefix}/"}},
        sort=[("_id", DESCENDING)]  # safer than string sort
    )

    if last_shift:
        match = re.search(r"/(\d+)$", last_shift["shiftno"])
        last_number = int(match.group(1)) if match else 0
    else:
        # ✅ No shift found for this FY → start again from 1
        last_number = 0

    new_number = last_number + 1

    return f"{prefix}/{new_number:06d}"




from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime




@api_view(["POST"])
@permission_classes([HasRolePermission])
def post_shiftdetails(request):
    action = request.data.get("action")
    employee_id = request.data.get("auth-user-id")

    mongo_url = os.getenv("GLOBAL_DB_HOST")
    client = MongoClient(mongo_url)
    db = client["ER_Billing"]
    collection = db["er_shiftdetails"]

    # ================= START SHIFT =================
    if action == "start":
        try:
            active_shift = collection.find_one({"is_active": True})
            if active_shift:
                return Response({
                    "error": f"Shift already running by Employee ID {active_shift.get('created_by')}"
                }, status=400)

            shift_number = generate_shift_number()

            shift_data = {
                "shiftno": shift_number,
                "starttime": datetime.utcnow(),
                "endtime": None,
                "is_active": True,
                "created_by": employee_id,
                "created_date": datetime.utcnow()
            }

            result = collection.insert_one(shift_data)
            shift_data["_id"] = str(result.inserted_id)

            return Response({"success": True, "data": shift_data}, status=201)

        except Exception as e:
            # Handles duplicate key error from unique index
            return Response({
                "error": "Shift is already running"
            }, status=400)

    # ================= END SHIFT =================
    elif action == "end":

        active_shift = collection.find_one({"is_active": True})

        if not active_shift:
            return Response({"error": "No active shift found"}, status=400)

        # Only shift owner can end it
        if active_shift.get("created_by") != employee_id:
            return Response({
                "error": "You cannot end another employee's shift"
            }, status=403)

        end_time = datetime.utcnow()

        collection.update_one(
            {"_id": active_shift["_id"]},
            {"$set": {"endtime": end_time, "is_active": False}}
        )

        active_shift["endtime"] = end_time
        active_shift["is_active"] = False
        active_shift["_id"] = str(active_shift["_id"])

        return Response({"success": True, "data": active_shift})

    return Response({"error": "Invalid action"}, status=400)



@api_view(["GET"])
@permission_classes([HasRolePermission])
def get_active_shift(request):
    mongo_url = os.getenv("GLOBAL_DB_HOST")
    client = MongoClient(mongo_url)
    db = client["ER_Billing"]
    collection = db["er_shiftdetails"]

    active_shift = collection.find_one({"is_active": True})

    if not active_shift:
        return Response({"is_active": False})

    active_shift["_id"] = str(active_shift["_id"])

    return Response({
        "is_active": True,
        "shiftno": active_shift["shiftno"],
        "starttime": active_shift["starttime"],
        "created_by": active_shift.get("created_by")
    })
