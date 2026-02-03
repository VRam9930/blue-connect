from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from database.db import users_collection, jobs_collection, applications_collection
from datetime import datetime, timedelta
from bson import ObjectId

whatsapp_bp = Blueprint("whatsapp", __name__)

# Fixed options
VILLAGES = [
    "అమలాపురం",
    "అనపర్తి",
    "బలభద్రాపురం",
    "బిక్కవోలు",
    "గొల్లల మామిడాడ",
    "కొమరిపాలెం",
    "పందలపాక",
    "పెదపూడి",
    "పెద్దాడ",
    "రామచంద్రపురం",
    "రాయవరం",
    "వేట్లపాలెం"
]


WORK_TYPES = [
    "వరి నాట్లు",
    "కలుపు తీయడం",
    "ఎరువులు / మందులు వేయడం",
    "వరి కోత",
    "తోట పని",
    "పొలాల శుభ్రపరిచే పని"
]

WORK_TYPE_ICONS = {
    "వరి నాట్లు": "🌱",
    "కలుపు తీయడం": "🌿",
    "ఎరువులు / మందులు వేయడం": "🧪",
    "వరి కోత": "🌾",
    "తోట పని": "🌳",
    "పొలాల శుభ్రపరిచే పని": "🧹"
}

@whatsapp_bp.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming = request.values.get("Body", "").strip()
    phone = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    user = users_collection.find_one({"phone": phone})

    # ================= NEW USER =================
    if not user:
        users_collection.insert_one({"phone": phone, "step": "menu"})
        msg.body(
                "నమస్తే రైతు బంధువులారా! 🙏🏼🌾\n\n"
                "మీకు హృదయపూర్వక స్వాగతం 🙌\n"
                "🤝 మీరు ఇప్పుడు 💙 *బ్లూ కనెక్* కుటుంబంలో ఒక భాగం!\n\n"
                "*బ్లూ కనెక్ట్ (Blue Connect)* టీం💙 ద్వారా మీరు పొందగలిగే సౌకర్యాలు:*\n"
                "☀️ వాతావరణ సమాచారం\n"
                "📈 రోజువారీ మార్కెట్ ధరలు\n"
                "🧑‍🌾 పంటలపై విలువైన సలహాలు\n"
                "📢 ప్రభుత్వ పథకాల అప్డేట్స్\n"
                "💼 వ్యవసాయ పనుల & కార్మికుల సమాచారం\n\n"
                "🌟 *ఇది పూర్తిగా ఉచితం!*\n"
                "మీ అభివృద్ధే మా లక్ష్యం 💪"
            )

        msg.body(
            "👉 మీరు ఎవరో ఎంచుకోండి:\n\n"
            "1️⃣ నేను రైతుని (పని ఇవ్వాలి)\n"
            "2️⃣ నేను కార్మికుని (పని కావాలి)"
        )

        return str(resp)

    step = user["step"]

    # ================= MENU =================
    if step == "menu":
        if incoming == "1":
            if "poster_name" in user and "poster_gender" in user and "poster_age" in user:
                users_collection.update_one(
                    {"phone": phone},
                    {"$set": {"step": "farmer_village"}}
                )
                msg.body(
                    f"🙏 {user['poster_name']} గారు,\n\n"
                    "📍 గ్రామం ఎంచుకోండి:\n\n"
                    + "\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)])
                )

            else:
                users_collection.update_one(
                    {"phone": phone},
                    {"$set": {"step": "farmer_name"}}
                )
                msg.body("👤 మీ పేరు నమోదు చేయండి")
        elif incoming == "2":
            users_collection.update_one(
                {"phone": phone},
                {"$set": {"step": "worker_gender"}}
            )
            msg.body(
                "👤 మీ లింగం ఎంచుకోండి:\n\n"
                "1️⃣👨పురుషుడు\n"
                "2️⃣👩మహిళ"
            )
        else:
            msg.body(
                "❓ మళ్లీ ఎంచుకోండి:\n\n"
                "1️⃣ నేను రైతుని (పని ఇవ్వాలి)\n"
                "2️⃣ నేను కార్మికుని (పని కావాలి)"
            )
        return str(resp)

    # ================= FARMER FLOW =================
    if step == "farmer_name":
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"poster_name": incoming, "step": "farmer_poster_gender"}}
        )
        msg.body(" మీ లింగం ఎంచుకోండి:\n1️⃣👨పురుషుడు \n2️⃣👩మహిళ ")
        return str(resp)

    if step == "farmer_poster_gender":
        if incoming not in ["1", "2"]:
            msg.body(
                "⚠️ సరైన ఎంపిక ఇవ్వలేదు\n\n"
                "దయచేసి పంపండి:\n"
                "1️⃣👨పురుషుడు\n"
                "2️⃣👩మహిళ"
            )

            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {
                "poster_gender": "male" if incoming == "1" else "female",
                "step": "farmer_poster_age"
            }}
        )
        msg.body("📅 మీ వయస్సు నమోదు చేయండి")
        return str(resp)

    if step == "farmer_poster_age":
        if not incoming.isdigit() or not (18 <= int(incoming) <= 80):
            msg.body("⚠️ వయస్సు 18 నుండి 80 మధ్య ఉండాలి")
            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"poster_age": int(incoming), "step": "farmer_village"}}
        )
        msg.body(
            "📍 *ఈ పని ఏ గ్రామంలో చేయాలి?*\n\n" +
            "\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)])
        )
        return str(resp)

    if step == "farmer_village":
        if not incoming.isdigit() or not (1 <= int(incoming) <= len(VILLAGES)):
            msg.body("⚠️ సరైన గ్రామ సంఖ్య పంపండి")
            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"area": VILLAGES[int(incoming)-1], "step": "farmer_work"}}
        )
        msg.body(
            "🌾 *పని రకం ఎంచుకోండి*\n\n" +
            "\n".join([
                f"{i+1}. {WORK_TYPE_ICONS[w]} {w}"
                for i, w in enumerate(WORK_TYPES)
            ])
        )

        return str(resp)

    if step == "farmer_work":
        if not incoming.isdigit() or not (1 <= int(incoming) <= len(WORK_TYPES)):
            msg.body("⚠️ సరైన పని రకం సంఖ్య పంపండి")
            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"work_type": WORK_TYPES[int(incoming)-1], "step": "farmer_wage"}}
        )
        msg.body("💰 రోజువారీ జీతం నమోదు చేయండి (₹400 – ₹1000)")
        return str(resp)

    if step == "farmer_wage":
        if not incoming.isdigit() or not (400 <= int(incoming) <= 1000):
            msg.body("⚠️ జీతం ₹400 నుండి ₹1000 మధ్య ఉండాలి")
            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"wage": int(incoming), "step": "farmer_worker_gender"}}
        )
        msg.body(
            "👥 ఎవరు కావాలి?\n\n"
            "1️⃣👨 పురుషులు\n"
            "2️⃣👩 మహిళలు\n"
            "3️⃣👨🏻‍🤝‍👩🏻 ఇద్దరూ"
        )

        return str(resp)

    if step == "farmer_worker_gender":
        gender_map = {"1": "male", "2": "female", "3": "both"}
        if incoming not in gender_map:
            msg.body(
                "⚠️ సరైన ఎంపిక ఇవ్వలేదు\n\n"
                "దయచేసి ఎంచుకోండి:\n"
                "1️⃣ 👨 పురుషులు\n"
                "2️⃣ 👩 మహిళలు\n"
                "3️⃣ 👨🏻‍🤝‍👩🏻 ఇద్దరూ"
            )

            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"gender_required": gender_map[incoming], "step": "farmer_count"}}
        )
        msg.body(
            "👥 ఎంత మంది అవసరం?\n\n"
            "👉 సంఖ్య మాత్రమే పంపండి (ఉదా: 5)"
        )

        return str(resp)

    if step == "farmer_count":
        if not incoming.isdigit():
            msg.body(
                "⚠️ సరైన సంఖ్య పంపండి\n"
                "(ఉదా: 5)"
            )
            return str(resp)

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

        msg.body(
            f"🙏 {user['poster_name']} గారు,\n\n"
            "మీ పని విజయవంతంగా నమోదు అయ్యింది! ✅\n\n"
            "📋 *పని వివరాలు:*\n"
            f"{WORK_TYPE_ICONS[user['work_type']]} పని: {user['work_type']}\n"
            f"📍 గ్రామం: {user['area']}\n"
            f"💰 రోజువారీ జీతం: ₹{user['wage']}\n\n"
            "👥 కార్మికులు త్వరలో మీకు కనెక్ట్ అవుతారు.\n"
            "⏳ *గమనిక:* ఈ పని 24 గంటల వరకు మాత్రమే కనిపిస్తుంది.\n\n"
            "📞 వెంటనే కాల్ వచ్చినప్పుడు స్పందించండి – ఖాళీలు త్వరగా నింపబడతాయి.\n\n"
            "ధన్యవాదాలు 🙏\n"
            "– మీ *బ్లూ కనెక్ట్ (Blue Connect)* టీం💙"
        )

        return str(resp)

    # ================= WORKER FLOW =================
    if step == "worker_gender":
        if incoming not in ["1", "2"]:
            msg.body(
                "⚠️ సరైన ఎంపిక ఇవ్వలేదు\n\n"
                "దయచేసి మీ లింగం ఎంచుకోండి:\n"
                "1️⃣ 👨 పురుషుడు\n"
                "2️⃣ 👩 మహిళ"
            )

            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"gender": "male" if incoming == "1" else "female", "step": "worker_village"}}
        )
        msg.body(
            "📍 మీరు పని చేయాలనుకున్న గ్రామం ఎంచుకోండి:\n\n" +
            "\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)])
        )
        return str(resp)

    if step == "worker_village":
        if not incoming.isdigit() or not (1 <= int(incoming) <= len(VILLAGES)):
            msg.body("⚠️ సరైన గ్రామ సంఖ్య పంపండి")
            return str(resp)

        area = VILLAGES[int(incoming)-1]
        valid_time = datetime.utcnow() - timedelta(hours=24)

        applied_ids = applications_collection.distinct(
            "job_id", {"worker_phone": phone}
        )

        jobs = list(jobs_collection.find({
            "_id": {"$nin": applied_ids},
            "area": area,
            "created_at": {"$gte": valid_time},
            "$expr": {"$lt": ["$persons_filled", "$persons_needed"]},
            "$or": [
                {"gender_required": user["gender"]},
                {"gender_required": "both"}
            ]
        }))

        if not jobs:
            msg.body(
                "❌ ప్రస్తుతం ఈ గ్రామంలో పనులు లేవు\n\n"
                "మళ్లీ ప్రారంభించాలంటే:\n"
                1️⃣ నేను రైతుని (పని ఇవ్వాలి)\n"
                2️⃣ నేను కార్మికుని (పని కావాలి)"
            )
            users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})
            return str(resp)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"step": "apply_job", "jobs": [str(j["_id"]) for j in jobs]}}
        )

        reply = "\n".join([
            f"{i+1}. {WORK_TYPE_ICONS[j['work_type']]} {j['work_type']} – ₹{j['wage']} | ఖాళీ స్థానాలు: {j['persons_needed'] - j['persons_filled']}"
            for i, j in enumerate(jobs)
        ])

        msg.body(
            "📋 *లభ్యమైన పనులు*\n\n" +
            reply +
            "\n\nఅప్లై చేయాలంటే పని సంఖ్య పంపండి"
        )
        return str(resp)

    if step == "apply_job":
        if not incoming.isdigit() or not (1 <= int(incoming) <= len(user["jobs"])):
            msg.body("⚠️ సరైన పని సంఖ్య పంపండి")
            return str(resp)

        job_id = ObjectId(user["jobs"][int(incoming)-1])
        job = jobs_collection.find_one({"_id": job_id})

        if applications_collection.find_one({"job_id": job_id, "worker_phone": phone}):
            msg.body(
                "❌ మీరు ఇప్పటికే ఈ పనికి అప్లై చేశారు\n\n"
                f"{WORK_TYPE_ICONS[job['work_type']]} పని: {job['work_type']}\n"
                f"📍 గ్రామం: {job['area']}\n"
                f"💰 జీతం: ₹{job['wage']}\n"
                f"📞 సంప్రదించండి: {job['contact']}"
            )
            users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})
            return str(resp)

        applications_collection.insert_one({
            "job_id": job_id,
            "worker_phone": phone,
            "applied_at": datetime.utcnow()
        })

        jobs_collection.update_one(
            {"_id": job_id},
            {"$inc": {"persons_filled": 1}}
        )

        users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})

        msg.body(
            "✅ *మీ అప్లికేషన్ విజయవంతమైంది!* 🙌\n\n"
            "📋 *మీరు అప్లై చేసిన పని వివరాలు:*\n\n"
            f"{WORK_TYPE_ICONS[job['work_type']]} పని: {job['work_type']}\n"
            f"📍 గ్రామం: {job['area']}\n"
            f"💰 రోజువారీ జీతం: ₹{job['wage']}\n\n"
            "👤 *పని ఇచ్చే వ్యక్తి సంప్రదింపు వివరాలు:*\n"
            f"📞 మొబైల్ నంబర్: {job['contact']}\n\n"
            "👉 దయచేసి వెంటనే పై నంబర్‌కు కాల్ చేసి\n"
            "పని గురించి మాట్లాడండి.\n\n"
            "⏳ ఆలస్యం చేస్తే అవకాశం కోల్పోయే అవకాశం ఉంది.\n\n"
            "ధన్యవాదాలు 🙏\n"
            "– మీ 💙*బ్లూ కనెక్ట్ (Blue Connect)* టీం"
        )

        return str(resp)

    # ================= FALLBACK =================
    msg.body(
        "⚠️ మీ సందేశం అర్థం కాలేదు\n\n"
        "మళ్లీ ప్రారంభించాలంటే:\n"
        "1️⃣ నేను రైతుని (పని ఇవ్వాలి)\n"
        "2️⃣ నేను కార్మికుని (పని కావాలి)"
    )
    users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})
    return str(resp)
