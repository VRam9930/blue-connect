from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from database.db import users_collection, jobs_collection, applications_collection
from datetime import datetime, timedelta
from bson import ObjectId

whatsapp_bp = Blueprint("whatsapp", __name__)

# Fixed options
VILLAGES = [
    "గుంటూరు", "తెనాలి", "మంగళగిరి", "చిలకలూరిపేట",
    "నరసరావుపేట", "బాపట్ల", "చీరాల",
    "పిడుగురాళ్ళ", "సత్తెనపల్లి", "వినుకొండ"
]

WORK_TYPES = [
    "నాట్లు", "కోత", "పంట తీయడం",
    "తోట పని", "పొలాల శుభ్రపరిచే పని"
]


@whatsapp_bp.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming = request.values.get("Body", "").strip()
    phone = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    user = users_collection.find_one({"phone": phone})

    # NEW USER
    if not user:
        users_collection.insert_one({"phone": phone, "step": "menu"})
        msg.body(
            "🙏 Blue Connect కు స్వాగతం\n\n"
            "1️⃣ పని ఇవ్వాలి\n"
            "2️⃣ పని కావాలి\n\n"
            "సంఖ్య పంపండి"
        )
        return str(resp)

    step = user["step"]

    # ================= MENU =================
    if step == "menu":
        if incoming == "1":
            users_collection.update_one({"phone": phone}, {"$set": {"step": "farmer_name"}})
            msg.body("మీ పేరు నమోదు చేయండి")
        elif incoming == "2":
            users_collection.update_one({"phone": phone}, {"$set": {"step": "worker_gender"}})
            msg.body("మీ లింగం:\n1️⃣ పురుషుడు\n2️⃣ మహిళ")
        else:
            msg.body("దయచేసి 1 లేదా 2 పంపండి")
        return str(resp)

    # ================= FARMER FLOW =================
    if step == "farmer_name":
        users_collection.update_one({"phone": phone}, {"$set": {"poster_name": incoming, "step": "farmer_poster_gender"}})
        msg.body("మీ లింగం:\n1️⃣ పురుషుడు\n2️⃣ మహిళ")
        return str(resp)

    if step == "farmer_poster_gender":
        if incoming not in ["1", "2"]:
            msg.body("1 లేదా 2 పంపండి")
            return str(resp)
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"poster_gender": "male" if incoming == "1" else "female", "step": "farmer_poster_age"}}
        )
        msg.body("మీ వయస్సు నమోదు చేయండి")
        return str(resp)

    if step == "farmer_poster_age":
        if not incoming.isdigit() or not (18 <= int(incoming) <= 80):
            msg.body("వయస్సు 18–80 మధ్య ఉండాలి")
            return str(resp)
        users_collection.update_one({"phone": phone}, {"$set": {"poster_age": int(incoming), "step": "farmer_village"}})
        msg.body("\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)]))
        return str(resp)

    if step == "farmer_village":
        idx = int(incoming) - 1
        users_collection.update_one({"phone": phone}, {"$set": {"area": VILLAGES[idx], "step": "farmer_work"}})
        msg.body("\n".join([f"{i+1}. {w}" for i, w in enumerate(WORK_TYPES)]))
        return str(resp)

    if step == "farmer_work":
        idx = int(incoming) - 1
        users_collection.update_one({"phone": phone}, {"$set": {"work_type": WORK_TYPES[idx], "step": "farmer_wage"}})
        msg.body("రోజువారీ జీతం ఎంత?")
        return str(resp)

    if step == "farmer_wage":
        if not incoming.isdigit() or not (400 <= int(incoming) <= 1000):
            msg.body("జీతం ₹400–₹1000 మధ్య ఉండాలి")
            return str(resp)
        users_collection.update_one({"phone": phone}, {"$set": {"wage": int(incoming), "step": "farmer_worker_gender"}})
        msg.body("ఎవరు కావాలి?\n1️⃣ పురుషులు\n2️⃣ మహిళలు\n3️⃣ ఇద్దరూ")
        return str(resp)

    if step == "farmer_worker_gender":
        gender_map = {"1": "male", "2": "female", "3": "both"}
        users_collection.update_one({"phone": phone}, {"$set": {"gender_required": gender_map[incoming], "step": "farmer_count"}})
        msg.body("ఎంత మంది అవసరం?")
        return str(resp)

    if step == "farmer_count":
        user = users_collection.find_one({"phone": phone})
        jobs_collection.insert_one({
            "area": user["area"],
            "work_type": user["work_type"],
            "wage": user["wage"],
            "gender_required": user["gender_required"],
            "persons_needed": int(incoming),
            "persons_filled": 0,
            "poster_name": user["poster_name"],
            "poster_gender": user["poster_gender"],
            "poster_age": user["poster_age"],
            "contact": phone,
            "created_at": datetime.utcnow()
        })
        users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})
        msg.body("✅ పని నమోదు అయ్యింది (24 గంటలు మాత్రమే కనిపిస్తుంది)")
        return str(resp)

    # ================= WORKER FLOW =================
    if step == "worker_gender":
        users_collection.update_one({"phone": phone}, {"$set": {"gender": "male" if incoming == "1" else "female", "step": "worker_village"}})
        msg.body("\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)]))
        return str(resp)

    if step == "worker_village":
        area = VILLAGES[int(incoming) - 1]
        valid_time = datetime.utcnow() - timedelta(hours=24)

        applied_ids = applications_collection.distinct("job_id", {"worker_phone": phone})

        jobs = list(jobs_collection.find({
            "_id": {"$nin": applied_ids},
            "area": area,
            "created_at": {"$gte": valid_time},
            "$expr": {"$lt": ["$persons_filled", "$persons_needed"]},
            "$or": [{"gender_required": user["gender"]}, {"gender_required": "both"}]
        }))

        if not jobs:
            msg.body("❌ పనులు లేవు")
            users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})
            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"step": "apply_job", "jobs": [str(j["_id"]) for j in jobs]}}
        )

        reply = "\n".join([f"{i+1}. {j['work_type']} – ₹{j['wage']} | ఖాళీ స్థానాలు: {j['persons_needed'] - j['persons_filled']}" for i, j in enumerate(jobs)])
        msg.body(reply + "\nఅప్లై చేయాలంటే సంఖ్య పంపండి")
        return str(resp)

    if step == "apply_job":
        job_id = ObjectId(user["jobs"][int(incoming) - 1])

        if applications_collection.find_one({"job_id": job_id, "worker_phone": phone}):
            msg.body("❌ మీరు ఇప్పటికే అప్లై చేశారు")
            return str(resp)

        applications_collection.insert_one({
            "job_id": job_id,
            "worker_phone": phone,
            "applied_at": datetime.utcnow()
        })

        jobs_collection.update_one({"_id": job_id}, {"$inc": {"persons_filled": 1}})
        users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})

        msg.body("✅ అప్లై అయ్యింది")
        return str(resp)

    msg.body("Hi పంపండి")
    users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})
    return str(resp)
