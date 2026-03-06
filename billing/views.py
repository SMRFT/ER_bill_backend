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

from datetime import datetime
from pymongo import MongoClient
import os

from datetime import datetime
from pymongo import MongoClient
import os

@api_view(['PUT'])
@permission_classes([HasRolePermission])
@parser_classes([JSONParser])
def update_billing_status(request, billnumber):
    bill = get_object_or_404(ERBilling, billnumber=billnumber)

    employee_id = request.data.get("auth-user-id")
    payload = request.data.get("data", {})

    payment_mode = payload.get("payment_mode")
    billing_status = payload.get("billing_status")

    if payment_mode is None:
        return Response({"error": "payment_mode is required"}, status=400)

    # ==========================================================
    # 🔴 STEP 1: CHECK ACTIVE SHIFT BEFORE ALLOWING PAYMENT
    # ==========================================================
    mongo_url = os.getenv("GLOBAL_DB_HOST")
    client = MongoClient(mongo_url)
    db = client["ER_Billing"]
    shift_collection = db["er_shiftdetails"]

    active_shift = shift_collection.find_one({"is_active": True})

    # ❌ BLOCK PAYMENT IF NO ACTIVE SHIFT
    if billing_status and billing_status.lower() == "paid" and not active_shift:
        return Response({
            "error": "No active shift. Please start the shift before processing payment."
        }, status=400)

    previous_status = bill.billing_status

    # ==========================================================
    # COMMON UPDATES
    # ==========================================================
    bill.payment_mode = payment_mode
    bill.billing_status = billing_status
    bill.lastmodified_by = employee_id
    bill.lastmodified_date = datetime.now()

    # ==========================================================
    # ✅ WHEN STATUS CHANGES FROM BILLED → PAID
    # ==========================================================
    if previous_status.lower() == "billed" and billing_status.lower() == "paid":

        # Save pharmacist id
        bill.pharmacist_id = employee_id

        # Attach shift number (guaranteed exists because we blocked above)
        bill.shiftno = active_shift.get("shiftno")

    bill.save()

    return Response({
        "message": "Updated successfully",
        "billing_status": bill.billing_status,
        "pharmacist_id": getattr(bill, "pharmacist_id", None),
        "shiftno": getattr(bill, "shiftno", None),
        "lastmodified_by": bill.lastmodified_by,
        "lastmodified_date": bill.lastmodified_date
    })


import os
import json
from pymongo import MongoClient
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
import pytz



@api_view(["GET"])
@permission_classes([HasRolePermission])
def get_shift_account_summary(request):

    mongo_url = os.getenv("GLOBAL_DB_HOST")
    client = MongoClient(mongo_url)

    # Databases
    er_db = client["ER_Billing"]
    shift_collection = er_db["er_shiftdetails"]
    billing_collection = er_db["billing_erbilling"]

    global_db = client["Global"]
    profile_collection = global_db["backend_diagnostics_profile"]

    from_date = request.GET.get("from")
    to_date = request.GET.get("to")

    date_filter = {}

    if from_date and to_date:
        ist = pytz.timezone("Asia/Kolkata")

        # Convert IST date → UTC for Mongo filtering
        start_day_ist = ist.localize(datetime.strptime(from_date, "%Y-%m-%d"))
        end_day_ist = ist.localize(
            datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        )

        start_day_utc = start_day_ist.astimezone(pytz.utc)
        end_day_utc = end_day_ist.astimezone(pytz.utc)

        date_filter = {
            "starttime": {
                "$gte": start_day_utc,
                "$lte": end_day_utc
            }
        }

    # Get shifts
    shifts = list(
        shift_collection.find(date_filter).sort("starttime", -1)
    )

    response_data = []

    for shift in shifts:

        shift_no = shift.get("shiftno")
        employee_id = str(shift.get("created_by"))

        # Employee lookup
        profile = profile_collection.find_one({
            "$or": [
                {"employeeId": employee_id},
                {"employeeId": int(employee_id) if employee_id.isdigit() else employee_id}
            ]
        })

        employee_name = profile.get("employeeName") if profile else "Unknown"

        # Bills strictly by shift number
        bills = list(billing_collection.find({
            "billing_status": "paid",
            "shiftno": shift_no
        }))

        total_amount = 0
        cash_total = 0
        digital_total = 0
        patient_details = []

        for bill in bills:

            bill_total = 0
            payment_modes = []

            modes = bill.get("payment_mode", [])

            if isinstance(modes, str):
                try:
                    modes = json.loads(modes)
                except:
                    modes = []

            if modes is None:
                modes = []

            for m in modes:

                amt = float(m.get("amount", 0))
                method = m.get("method", "").lower()

                bill_total += amt

                if method == "cash":
                    cash_total += amt
                else:
                    digital_total += amt

                payment_modes.append({
                    "method": method,
                    "amount": amt
                })

            total_amount += bill_total

            procedures = bill.get("procedures", [])

            if isinstance(procedures, str):
                try:
                    procedures = json.loads(procedures)
                except:
                    procedures = []

            patient_details.append({
                "patientname": bill.get("patientname"),
                "uhid": bill.get("uhid"),
                "billnumber": bill.get("billnumber"),
                "procedures": procedures,
                "payments": payment_modes,
                "total": bill_total
            })

        response_data.append({
            "shiftno": shift_no,
            "employee_name": employee_name,
            "starttime": shift.get("starttime"),
            "endtime": shift.get("endtime"),
            "cash_total": cash_total,
            "digital_total": digital_total,
            "total_amount": total_amount,
            "patients": patient_details
        })

    return JsonResponse({
        "success": True,
        "data": response_data
    }, safe=False)

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

    # ER Billing DB
    er_db = client["ER_Billing"]
    shift_collection = er_db["er_shiftdetails"]

    # Global DB
    global_db = client["Global"]
    profile_collection = global_db["backend_diagnostics_profile"]

    # Find active shift
    active_shift = shift_collection.find_one({"is_active": True})

    if not active_shift:
        return Response({"is_active": False})

    created_by = active_shift.get("created_by")
    created_by_name = None

    # Lookup employee name
    if created_by:
        profile = profile_collection.find_one(
            {"employeeId": str(created_by)},
            {"employeeName": 1}
        )
        if profile:
            created_by_name = profile.get("employeeName")

    return Response({
        "is_active": True,
        "shiftno": active_shift.get("shiftno"),
        "starttime": active_shift.get("starttime"),
        "created_by": created_by,
        "created_by_name": created_by_name
    })




# views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from pymongo import MongoClient
from datetime import datetime, timedelta
import os, json
from collections import defaultdict



@api_view(["POST"])
@permission_classes([HasRolePermission])
def get_pharmacist_shiftreport(request):

    from_date = request.data.get("from_date")
    to_date = request.data.get("to_date")

    if not from_date or not to_date:
        return Response({"error": "From and To date required"}, status=400)

    mongo_url = os.getenv("GLOBAL_DB_HOST")
    client = MongoClient(mongo_url)

    er_db = client["ER_Billing"]
    shift_collection = er_db["er_shiftdetails"]
    billing_collection = er_db["billing_erbilling"]

    global_db = client["Global"]
    profile_collection = global_db["backend_diagnostics_profile"]

    # ✅ CLOSED SHIFTS IN DATE RANGE
    shift_filter = {
        "starttime": {
            "$gte": datetime.strptime(from_date, "%Y-%m-%d"),
            "$lte": datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
        },
        
    }

    shifts = list(shift_collection.find(shift_filter))
    report = []

    for shift in shifts:
        shiftno = shift.get("shiftno")

        bills = list(billing_collection.find({
            "shiftno": shiftno,
            "billing_status": "paid"
        }))

        cash_total = 0
        card_total = 0
        upi_total = 0
        pharmacist_ids = set()

        for bill in bills:
            pharmacist_id = bill.get("pharmacist_id")
            if pharmacist_id:
                pharmacist_ids.add(pharmacist_id)

            payments = bill.get("payment_mode", [])
            if isinstance(payments, str):
                try:
                    payments = json.loads(payments)
                except:
                    payments = []

            for pay in payments:
                method = str(pay.get("method", "")).lower()
                amount = float(pay.get("amount", 0))

                if method == "cash":
                    cash_total += amount
                elif method == "card":
                    card_total += amount
                elif method == "upi":
                    upi_total += amount

        bank_total = card_total + upi_total
        grand_total = cash_total + bank_total

        # ✅ MAP PHARMACIST ID → NAME
        collected_by = "-"
        if pharmacist_ids:
            profile = profile_collection.find_one(
                {"employeeId": list(pharmacist_ids)[0]},
                {"employeeName": 1}
            )
            if profile:
                collected_by = profile.get("employeeName", "-")

        if grand_total > 0:
            report.append({
                "shiftno": shiftno,
                "starttime": shift.get("starttime"),
                "endtime": shift.get("endtime"),
                "cash_total": round(cash_total, 2),
                "card_total": round(card_total, 2),
                "upi_total": round(upi_total, 2),
                "bank_total": round(bank_total, 2),
                "grand_total": round(grand_total, 2),
                "collected_by": collected_by
            })

    report.sort(key=lambda x: x["starttime"])
    return Response(report)






from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from pymongo import MongoClient
from datetime import datetime, timedelta
import os

@api_view(["POST"])
@permission_classes([HasRolePermission])
def View_bills_report(request):
    try:
        mongo_url = os.getenv("GLOBAL_DB_HOST")
        client = MongoClient(mongo_url)

        er_db = client["ER_Billing"]
        billing_collection = er_db["billing_erbilling"]

        global_db = client["Global"]
        profile_collection = global_db["backend_diagnostics_profile"]

        from_date = request.data.get("from_date")
        to_date = request.data.get("to_date")
        search_by = request.data.get("search_by")
        search_value = request.data.get("search_value")

        if not from_date or not to_date:
            return Response(
                {"message": "from_date and to_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        start = datetime.strptime(from_date, "%Y-%m-%d")
        end = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)

        query = {
            "date": {"$gte": start, "$lt": end}
        }

        # Dynamic filters
        if search_by and search_value:
            if search_by == "uhid":
                query["uhid"] = search_value

            elif search_by == "patientname":
                query["patientname"] = {"$regex": search_value, "$options": "i"}

            elif search_by == "status":
                query["billing_status"] = search_value

            elif search_by == "paymentmode":
                query["payment_mode"] = {
                    "$regex": search_value, "$options": "i"
                }

        bills = list(billing_collection.find(query))

        if not bills:
            return Response(
                {"message": "No patient found"},
                status=status.HTTP_200_OK
            )

        # Fetch employee map
        employee_map = {
            emp["employeeId"]: emp.get("employeeName", "")
            for emp in profile_collection.find({}, {"employeeId": 1, "employeeName": 1})
        }

        response = []
        for bill in bills:
            response.append({
                "bill_date": bill["date"].strftime("%Y-%m-%d"),
                "bill_time": bill["date"].strftime("%H:%M:%S"),
                "patientname": bill.get("patientname"),
                "uhid": bill.get("uhid"),
                "payment_mode": bill.get("payment_mode"),
                "status": bill.get("billing_status"),
                "billnumber": bill.get("billnumber"),
                "total": bill.get("total"),
                "shiftno": bill.get("shiftno"),
                "billed_by": employee_map.get(bill.get("created_by"), "")
            })

        return Response(response, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
