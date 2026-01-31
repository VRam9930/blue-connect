from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from database.db import users_collection, jobs_collection
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
        users_collection.insert_one({
            "phone": phone,
            "step": "menu"
        })
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
            users_collection.update_one(
                {"phone": phone},
                {"$set": {"step": "farmer_name"}}
            )
            msg.body("మీ పేరు నమోదు చేయండి")
        elif incoming == "2":
            users_collection.update_one(
                {"phone": phone},
                {"$set": {"step": "worker_gender"}}
            )
            msg.body("మీ లింగం:\n1️⃣ పురుషుడు\n2️⃣ మహిళ")
        else:
            msg.body("దయచేసి 1 లేదా 2 పంపండి")
        return str(resp)

    # ================= FARMER FLOW =================

    # FARMER NAME
    if step == "farmer_name":
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"poster_name": incoming, "step": "farmer_poster_gender"}}
        )
        msg.body("మీ లింగం:\n1️⃣ పురుషుడు\n2️⃣ మహిళ")
        return str(resp)

    # FARMER GENDER
    if step == "farmer_poster_gender":
        if incoming not in ["1", "2"]:
            msg.body("1 లేదా 2 పంపండి")
            return str(resp)

        poster_gender = "male" if incoming == "1" else "female"
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"poster_gender": poster_gender, "step": "farmer_poster_age"}}
        )
        msg.body("మీ వయస్సు నమోదు చేయండి")
        return str(resp)

    # FARMER AGE
    if step == "farmer_poster_age":
        if not incoming.isdigit():
            msg.body("సరైన వయస్సు ఇవ్వండి")
            return str(resp)

        age = int(incoming)
        if age < 18 or age > 80:
            msg.body("వయస్సు 18 నుండి 80 మధ్య ఉండాలి")
            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"poster_age": age, "step": "farmer_village"}}
        )
        msg.body(
            "మీ గ్రామం ఎంచుకోండి:\n" +
            "\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)])
        )
        return str(resp)

    # FARMER VILLAGE
    if step == "farmer_village":
        idx = int(incoming) - 1
        if idx < 0 or idx >= len(VILLAGES):
            msg.body("సరైన సంఖ్య పంపండి")
            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"area": VILLAGES[idx], "step": "farmer_work"}}
        )
        msg.body(
            "పని రకం ఎంచుకోండి:\n" +
            "\n".join([f"{i+1}. {w}" for i, w in enumerate(WORK_TYPES)])
        )
        return str(resp)

    # FARMER WORK TYPE
    if step == "farmer_work":
        idx = int(incoming) - 1
        if idx < 0 or idx >= len(WORK_TYPES):
            msg.body("సరైన సంఖ్య పంపండి")
            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"work_type": WORK_TYPES[idx], "step": "farmer_wage"}}
        )
        msg.body("రోజువారీ జీతం ఎంత?")
        return str(resp)

    # FARMER WAGE
    if step == "farmer_wage":
        if not incoming.isdigit():
            msg.body("దయచేసి సంఖ్యలో జీతం ఇవ్వండి")
            return str(resp)
    
        wage = int(incoming)
    
        if wage < 400 or wage > 1000:
            msg.body("❌ జీతం ₹400 నుండి ₹1000 మధ్య ఉండాలి")
            return str(resp)
    
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"wage": wage, "step": "farmer_worker_gender"}}
        )
    
        msg.body("ఎవరు కావాలి?\n1️⃣ పురుషులు\n2️⃣ మహిళలు\n3️⃣ ఇద్దరూ")
        return str(resp)


    # REQUIRED WORKER GENDER
    if step == "farmer_worker_gender":
        gender_map = {"1": "male", "2": "female", "3": "both"}
        if incoming not in gender_map:
            msg.body("1 / 2 / 3 పంపండి")
            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"gender_required": gender_map[incoming], "step": "farmer_count"}}
        )
        msg.body("ఎంత మంది అవసరం?")
        return str(resp)

    # REQUIRED COUNT + SAVE JOB
    if step == "farmer_count":
        if not incoming.isdigit():
            msg.body("సంఖ్య ఇవ్వండి")
            return str(resp)

        user = users_collection.find_one({"phone": phone})

        jobs_collection.insert_one({
            "area": user["area"],
            "work_type": user["work_type"],
            "wage": user["wage"],
            "gender_required": user["gender_required"],
            "persons_needed": int(incoming),
            "persons_filled": 0,

            # JOB POSTER DETAILS
            "poster_name": user["poster_name"],
            "poster_gender": user["poster_gender"],
            "poster_age": user["poster_age"],

            "contact": phone,
            "created_at": datetime.utcnow()
        })

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"step": "menu"}}
        )

        msg.body("✅ మీ పని విజయవంతంగా నమోదు అయ్యింది (24 గంటల వరకు మాత్రమే కనిపిస్తుంది)")
        return str(resp)

    # ================= WORKER FLOW =================

    # WORKER GENDER
    if step == "worker_gender":
        if incoming not in ["1", "2"]:
            msg.body("1 లేదా 2 పంపండి")
            return str(resp)

        gender = "male" if incoming == "1" else "female"
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"gender": gender, "step": "worker_village"}}
        )
        msg.body(
            "గ్రామం ఎంచుకోండి:\n" +
            "\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)])
        )
        return str(resp)

    # WORKER VILLAGE SEARCH
    if step == "worker_village":
        idx = int(incoming) - 1
        if idx < 0 or idx >= len(VILLAGES):
            msg.body("సరైన సంఖ్య పంపండి")
            return str(resp)

        area = VILLAGES[idx]
        user = users_collection.find_one({"phone": phone})
        valid_time = datetime.utcnow() - timedelta(hours=24)

        jobs = list(jobs_collection.find({
            "area": area,
            "created_at": {"$gte": valid_time},
            "$expr": {"$lt": ["$persons_filled", "$persons_needed"]},
            "$or": [
                {"gender_required": user["gender"]},
                {"gender_required": "both"}
            ]
        }))

        if not jobs:
            msg.body("❌ ప్రస్తుతం పనులు లేవు")
            users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})
            return str(resp)

        reply = "పనులు:\n"
        for i, job in enumerate(jobs):
            reply += (
                f"\n{i+1}. {job['work_type']} – ₹{job['wage']}"
                f" – మిగిలినవి: {job['persons_needed'] - job['persons_filled']}"
            )

        reply += "\n\nఅప్లై చేయాలంటే సంఖ్య పంపండి"

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"step": "apply_job", "jobs": [str(j["_id"]) for j in jobs]}}
        )

        msg.body(reply)
        return str(resp)

    # APPLY JOB
    if step == "apply_job":
        idx = int(incoming) - 1
        job_id = user["jobs"][idx]

        job = jobs_collection.find_one({"_id": ObjectId(job_id)})

        if job["persons_filled"] >= job["persons_needed"]:
            msg.body("❌ ఈ పని ఇప్పటికే పూర్తయ్యింది")
            users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})
            return str(resp)

        jobs_collection.update_one(
            {"_id": job["_id"]},
            {"$inc": {"persons_filled": 1}}
        )

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"step": "menu"}}
        )

        msg.body(
            "✅ అప్లై అయ్యింది\n"
            f"📞 సంప్రదించండి: {job['contact']}"
        )
        return str(resp)

    # FALLBACK
    users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})
    msg.body("Hi పంపండి")
    return str(resp)
