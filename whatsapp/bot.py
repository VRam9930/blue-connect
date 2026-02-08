import os
from flask import Blueprint, request
import requests
from database.db import users_collection, jobs_collection, applications_collection
from datetime import datetime, timedelta
from bson import ObjectId

whatsapp_bp = Blueprint("whatsapp", __name__)

META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")
META_API_VERSION = os.getenv("META_API_VERSION", "v19.0")


def send_text_message(to_number, text):
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        return False

    url = f"https://graph.facebook.com/{META_API_VERSION}/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }

    try:
        requests.post(url, headers=headers, json=payload, timeout=10)
    except requests.RequestException:
        return False
    return True


def reply(phone, text):
    if phone and text:
        send_text_message(phone, text)


def extract_incoming_message(data):
    try:
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                if not messages:
                    continue
                msg = messages[0]
                text = msg.get("text", {}).get("body", "").strip()
                from_number = msg.get("from")
                return from_number, text
    except AttributeError:
        return None, ""
    return None, ""

# Fixed options
VILLAGES = [
    "అనపర్తి",
    "బలభద్రాపురం",
    "బిక్కవోలు",
    "గొల్లల మామిడాడ",
    "పందలపాక",
    "పెదపూడి",
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

@whatsapp_bp.route("/whatsapp", methods=["GET", "POST"])
def whatsapp_bot():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == META_VERIFY_TOKEN:
            return challenge, 200
        return "Forbidden", 403

    data = request.get_json(silent=True) or {}
    phone, incoming = extract_incoming_message(data)
    if not phone:
        return "OK", 200

    user = users_collection.find_one({"phone": phone})

    # ================= NEW USER =================
    if not user:
        users_collection.insert_one({"phone": phone, "step": "menu"})
        reply(
            phone,
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

        reply(
            phone,
            "👉 మీరు ఎవరో ఎంచుకోండి:\n\n"
            "1️⃣ నేను రైతుని (పని ఇవ్వాలి)\n"
            "2️⃣ నేను కార్మికుని (పని కావాలి)"
        )

        return "OK", 200

    step = user["step"]

    # ================= MENU =================
    if step == "menu":
        if incoming == "1":
            if "poster_name" in user and "poster_gender" in user and "poster_age" in user:
                users_collection.update_one(
                    {"phone": phone},
                    {"$set": {"step": "farmer_village"}}
                )
                reply(
                    phone,
                    f"🙏 {user['poster_name']} గారు,\n\n"
                    "📍 గ్రామం ఎంచుకోండి:\n\n"
                    + "\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)])
                    + "\n\nఉదా: 1"
                )

            else:
                users_collection.update_one(
                    {"phone": phone},
                    {"$set": {"step": "farmer_name"}}
                )
                reply(phone, "👤 మీ పేరు నమోదు చేయండి\nఉదా: రవి")
        elif incoming == "2":
            users_collection.update_one(
                {"phone": phone},
                {"$set": {"step": "worker_gender"}}
            )
            reply(
                phone,
                "👤 మీ లింగం ఎంచుకోండి:\n\n"
                "1️⃣👨పురుషుడు\n"
                "2️⃣👩మహిళ\n\n"
                "ఉదా: 1"
            )
        else:
            reply(
                phone,
                "❓ మళ్లీ ఎంచుకోండి:\n\n"
                "1️⃣ నేను రైతుని (పని ఇవ్వాలి)\n"
                "2️⃣ నేను కార్మికుని (పని కావాలి)"
            )
        return "OK", 200

    # ================= FARMER FLOW =================
    if step == "farmer_name":
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"poster_name": incoming, "step": "farmer_poster_gender"}}
        )
        reply(phone, " మీ లింగం ఎంచుకోండి:\n1️⃣👨పురుషుడు \n2️⃣👩మహిళ ")
        return "OK", 200

    if step == "farmer_poster_gender":
        if incoming not in ["1", "2"]:
            reply(
                phone,
                "⚠️ సరైన ఎంపిక ఇవ్వలేదు\n\n"
                "దయచేసి పంపండి:\n"
                "1️⃣👨పురుషుడు\n"
                "2️⃣👩మహిళ"
            )

            return "OK", 200

        users_collection.update_one(
            {"phone": phone},
            {"$set": {
                "poster_gender": "male" if incoming == "1" else "female",
                "step": "farmer_poster_age"
            }}
        )
        reply(phone, "📅 మీ వయస్సు నమోదు చేయండి\nఉదా: 35")
        return "OK", 200

    if step == "farmer_poster_age":
        if not incoming.isdigit() or not (18 <= int(incoming) <= 80):
            reply(phone, "⚠️ వయస్సు 18 నుండి 80 మధ్య ఉండాలి")
            return "OK", 200

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"poster_age": int(incoming), "step": "farmer_village"}}
        )
        reply(
            phone,
            "📍 *ఈ పని ఏ గ్రామంలో చేయాలి?*\n\n" +
            "\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)])
            + "\n\nఉదా: 1"
        )
        return "OK", 200

    if step == "farmer_village":
        if not incoming.isdigit() or not (1 <= int(incoming) <= len(VILLAGES)):
            reply(phone, "⚠️ సరైన గ్రామ సంఖ్య పంపండి")
            return "OK", 200

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"area": VILLAGES[int(incoming)-1], "step": "farmer_work"}}
        )
        reply(
            phone,
            "🌾 *పని రకం ఎంచుకోండి*\n\n" +
            "\n".join([
                f"{i+1}. {WORK_TYPE_ICONS[w]} {w}"
                for i, w in enumerate(WORK_TYPES)
            ])
            + "\n\nఉదా: 1"
        )

        return "OK", 200

    if step == "farmer_work":
        if not incoming.isdigit() or not (1 <= int(incoming) <= len(WORK_TYPES)):
            reply(phone, "⚠️ సరైన పని రకం సంఖ్య పంపండి")
            return "OK", 200

        user = users_collection.find_one({"phone": phone})
        selected_work = WORK_TYPES[int(incoming)-1]
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"work_type": selected_work}}
        )

        if user.get("edit_mode"):
            users_collection.update_one(
                {"phone": phone},
                {"$set": {"step": "farmer_confirm", "edit_mode": False}}
            )
            reply(
                phone,
                "📋 మీ పని వివరాలు:\n\n"
                f"{WORK_TYPE_ICONS[selected_work]} పని: {selected_work}\n"
                f"📍 గ్రామం: {user['area']}\n"
                f"💰 జీతం: ₹{user['wage']}\n"
                f"👥 కావలసినవారు: "
                + ("పురుషులు" if user['gender_required'] == "male" else "మహిళలు" if user['gender_required'] == "female" else "ఇద్దరూ") +
                f"\n🔢 అవసరం: {user.get('persons_needed', 0)} మంది\n\n"
                "1️⃣ నిర్ధారించండి (Post)\n"
                "2️⃣ మార్చాలి (Edit)"
            )
            return "OK", 200

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"step": "farmer_wage"}}
        )
        reply(phone, "💰 రోజువారీ జీతం నమోదు చేయండి (₹400 – ₹1000)")
        return "OK", 200

    if step == "farmer_wage":
        if not incoming.isdigit() or not (400 <= int(incoming) <= 1000):
            reply(phone, "⚠️ జీతం ₹400 నుండి ₹1000 మధ్య ఉండాలి")
            return "OK", 200

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"wage": int(incoming), "step": "farmer_worker_gender"}}
        )
        reply(
            phone,
            "👥 ఎవరు కావాలి?\n\n"
            "1️⃣👨 పురుషులు\n"
            "2️⃣👩 మహిళలు\n"
            "3️⃣👨🏻‍🤝‍👩🏻 ఇద్దరూ\n\n"
            "ఉదా: 1"
        )

        return "OK", 200

    if step == "farmer_worker_gender":
        gender_map = {"1": "male", "2": "female", "3": "both"}
        if incoming not in gender_map:
            reply(
                phone,
                "⚠️ సరైన ఎంపిక ఇవ్వలేదు\n\n"
                "దయచేసి ఎంచుకోండి:\n"
                "1️⃣ 👨 పురుషులు\n"
                "2️⃣ 👩 మహిళలు\n"
                "3️⃣ 👨🏻‍🤝‍👩🏻 ఇద్దరూ"
            )

            return "OK", 200

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"gender_required": gender_map[incoming], "step": "farmer_count"}}
        )
        reply(
            phone,
            "👥 ఎంత మంది అవసరం?\n\n"
            "👉 సంఖ్య మాత్రమే పంపండి (ఉదా: 5)"
        )

        return "OK", 200

    if step == "farmer_count":
        if not incoming.isdigit():
            reply(
                phone,
                "⚠️ సరైన సంఖ్య పంపండి\n"
                "(ఉదా: 5)"
            )
            return "OK", 200

        user = users_collection.find_one({"phone": phone})

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"persons_needed": int(incoming), "step": "farmer_confirm"}}
        )

        reply(
            phone,
            "📋 మీ పని వివరాలు:\n\n"
            f"{WORK_TYPE_ICONS[user['work_type']]} పని: {user['work_type']}\n"
            f"📍 గ్రామం: {user['area']}\n"
            f"💰 జీతం: ₹{user['wage']}\n"
            f"👥 కావలసినవారు: "
            + ("పురుషులు" if user['gender_required'] == "male" else "మహిళలు" if user['gender_required'] == "female" else "ఇద్దరూ") +
            f"\n🔢 అవసరం: {incoming} మంది\n\n"
            "1️⃣ నిర్ధారించండి (Post)\n"
            "2️⃣ మార్చాలి (Edit)"
        )

        return "OK", 200

    if step == "farmer_confirm":
        user = users_collection.find_one({"phone": phone})

        if incoming == "1":
            # Post the job
            jobs_collection.insert_one({
                "area": user["area"],
                "work_type": user["work_type"],
                "wage": user["wage"],
                "gender_required": user["gender_required"],
                "persons_needed": user["persons_needed"],
                "persons_filled": 0,
                "poster_name": user["poster_name"],
                "poster_gender": user["poster_gender"],
                "poster_age": user["poster_age"],
                "contact": phone,
                "created_at": datetime.utcnow()
            })

            users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})

            reply(
                phone,
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

        elif incoming == "2":
            # Edit option
            reply(
                phone,
                "✏️ ఏది మార్చాలి అనుకుంటున్నారు?\n\n"
                "1. గ్రామం\n"
                "2. పని రకం\n"
                "3. జీతం\n"
                "4. కావలసిన లింగం\n"
                "5. కార్మికుల సంఖ్య"
            )
            users_collection.update_one({"phone": phone}, {"$set": {"step": "farmer_edit_choice"}})

        else:
            reply(
                phone,
                "⚠️ సరైన ఎంపిక ఇవ్వలేదు\n\n"
                "1️⃣ నిర్ధారించండి\n"
                "2️⃣ మార్చాలి"
            )

        return "OK", 200

    if step == "farmer_edit_choice":
        edit_map = {
            "1": "farmer_village",
            "2": "farmer_work",
            "3": "farmer_wage",
            "4": "farmer_worker_gender",
            "5": "farmer_count"
        }

        if incoming not in edit_map:
            reply(
                phone,
                "⚠️ సరైన ఎంపిక ఇవ్వలేదు\n\n"
                "1. గ్రామం\n"
                "2. పని రకం\n"
                "3. జీతం\n"
                "4. కావలసిన లింగం\n"
                "5. కార్మికుల సంఖ్య"
            )
            return "OK", 200

        # Prompt based on edit choice
        if incoming == "1":
            reply(
                phone,
                "📍 *గ్రామం ఎంచుకోండి:*\n\n" +
                "\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)])
            )
        elif incoming == "2":
            reply(
                phone,
                "🌾 *పని రకం ఎంచుకోండి*\n\n" +
                "\n".join([
                    f"{i+1}. {WORK_TYPE_ICONS[w]} {w}"
                    for i, w in enumerate(WORK_TYPES)
                ])
            )
        elif incoming == "3":
            reply(phone, "💰 రోజువారీ జీతం నమోదు చేయండి (₹400 – ₹1000)")
        elif incoming == "4":
            reply(
                phone,
                "👥 ఎవరు కావాలి?\n\n"
                "1️⃣👨 పురుషులు\n"
                "2️⃣👩 మహిళలు\n"
                "3️⃣👨🏻‍🤝‍👩🏻 ఇద్దరూ"
            )
        elif incoming == "5":
            reply(phone, "👥 ఎంత మంది అవసరం?\n\n👉 సంఖ్య మాత్రమే పంపండి (ఉదా: 5)")

        users_collection.update_one({"phone": phone}, {"$set": {"step": edit_map[incoming], "edit_mode": True}})
        return "OK", 200

    # ================= WORKER FLOW =================
    if step == "worker_gender":
        if incoming not in ["1", "2"]:
            reply(
                phone,
                "⚠️ సరైన ఎంపిక ఇవ్వలేదు\n\n"
                "దయచేసి మీ లింగం ఎంచుకోండి:\n"
                "1️⃣ 👨 పురుషుడు\n"
                "2️⃣ 👩 మహిళ"
            )

            return "OK", 200

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"gender": "male" if incoming == "1" else "female", "step": "worker_village"}}
        )
        reply(
            phone,
            "📍 మీరు పని చేయాలనుకున్న గ్రామం ఎంచుకోండి:\n\n" +
            "\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)])
            + "\n\nఉదా: 1"
        )
        return "OK", 200

    if step == "worker_village":
        if not incoming.isdigit() or not (1 <= int(incoming) <= len(VILLAGES)):
            reply(phone, "⚠️ సరైన గ్రామ సంఖ్య పంపండి")
            return "OK", 200

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
            reply(
                phone,
                "❌ ప్రస్తుతం ఈ గ్రామంలో పనులు లేవు\n\n"
                "మళ్లీ ప్రారంభించాలంటే:\n"
                "1️⃣ నేను రైతుని (పని ఇవ్వాలి)\n"
                "2️⃣ నేను కార్మికుని (పని కావాలి)"
            )
            users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})
            return "OK", 200

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"step": "apply_job", "jobs": [str(j["_id"]) for j in jobs]}}
        )

        job_list = "\n".join([
            f"{i+1}. {WORK_TYPE_ICONS[j['work_type']]} {j['work_type']} – ₹{j['wage']} | ఖాళీ స్థానాలు: {j['persons_needed'] - j['persons_filled']}"
            for i, j in enumerate(jobs)
        ])

        reply(
            phone,
            "📋 *లభ్యమైన పనులు*\n\n" +
            job_list +
            "\n\nఅప్లై చేయాలంటే పని సంఖ్య పంపండి"
        )
        return "OK", 200

    if step == "apply_job":
        if not incoming.isdigit() or not (1 <= int(incoming) <= len(user["jobs"])):
            reply(phone, "⚠️ సరైన పని సంఖ్య పంపండి")
            return "OK", 200

        job_id = ObjectId(user["jobs"][int(incoming)-1])
        job = jobs_collection.find_one({"_id": job_id})

        if applications_collection.find_one({"job_id": job_id, "worker_phone": phone}):
            reply(
                phone,
                "❌ మీరు ఇప్పటికే ఈ పనికి అప్లై చేశారు\n\n"
                f"{WORK_TYPE_ICONS[job['work_type']]} పని: {job['work_type']}\n"
                f"📍 గ్రామం: {job['area']}\n"
                f"💰 జీతం: ₹{job['wage']}\n"
                f"📞 సంప్రదించండి: {job['contact']}"
            )
            users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})
            return "OK", 200

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

        reply(
            phone,
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

        return "OK", 200

    # ================= FALLBACK =================
    reply(
        phone,
        "⚠️ మీ సందేశం అర్థం కాలేదు\n\n"
        "మళ్లీ ప్రారంభించాలంటే:\n"
        "1️⃣ నేను రైతుని (పని ఇవ్వాలి)\n"
        "2️⃣ నేను కార్మికుని (పని కావాలి)"
    )
    users_collection.update_one({"phone": phone}, {"$set": {"step": "menu"}})
    return "OK", 200
