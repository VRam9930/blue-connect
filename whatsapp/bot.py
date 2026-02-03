from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client  # FEATURE 2: For farmer notifications
from database.db import users_collection, jobs_collection, applications_collection
from datetime import datetime, timedelta
from bson import ObjectId
import os

whatsapp_bp = Blueprint("whatsapp", __name__)

# FEATURE 2: Twilio client for sending farmer notifications
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")  # Default sandbox number
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN else None

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

        # FEATURE 1: Store job details in temp_job session object (not in jobs_collection yet)
        temp_job = {
            "area": user["area"],
            "work_type": user["work_type"],
            "wage": user["wage"],
            "gender_required": user["gender_required"],
            "persons_needed": int(incoming)
        }

        # FEATURE 1: Display gender in Telugu for acknowledgement
        gender_display = {"male": "పురుషులు", "female": "మహిళలు", "both": "ఇద్దరూ"}

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"temp_job": temp_job, "step": "farmer_confirm"}}
        )

        # FEATURE 1: Show acknowledgement message with job summary
        msg.body(
            f"🙏 {user['poster_name']} గారు,\n\n"
            "📋 *మీరు నమోదు చేసిన వివరాలు:*\n\n"
            f"{WORK_TYPE_ICONS[temp_job['work_type']]} పని: {temp_job['work_type']}\n"
            f"📍 గ్రామం: {temp_job['area']}\n"
            f"💰 రోజువారీ జీతం: ₹{temp_job['wage']}\n"
            f"👥 అవసరం: {gender_display[temp_job['gender_required']]}\n"
            f"🔢 సంఖ్య: {temp_job['persons_needed']} మంది\n\n"
            "దయచేసి ఎంచుకోండి:\n\n"
            "1️⃣ ధృవీకరించండి & పోస్ట్ చేయండి\n"
            "2️⃣ వివరాలు సవరించండి"
        )

        return str(resp)

    # FEATURE 1: Handle farmer confirmation or edit choice
    if step == "farmer_confirm":
        if incoming == "1":
            # FEATURE 1: Farmer confirmed - insert job into database
            user = users_collection.find_one({"phone": phone})
            temp_job = user["temp_job"]

            jobs_collection.insert_one({
                "area": temp_job["area"],
                "work_type": temp_job["work_type"],
                "wage": temp_job["wage"],
                "gender_required": temp_job["gender_required"],
                "persons_needed": temp_job["persons_needed"],
                "persons_filled": 0,
                "poster_name": user["poster_name"],
                "poster_gender": user["poster_gender"],
                "poster_age": user["poster_age"],
                "contact": phone,
                "created_at": datetime.utcnow()
            })

            users_collection.update_one(
                {"phone": phone},
                {"$set": {"step": "menu"}, "$unset": {"temp_job": ""}}
            )

            msg.body(
                f"🙏 {user['poster_name']} గారు,\n\n"
                "మీ పని విజయవంతంగా నమోదు అయ్యింది! ✅\n\n"
                "📋 *పని వివరాలు:*\n"
                f"{WORK_TYPE_ICONS[temp_job['work_type']]} పని: {temp_job['work_type']}\n"
                f"📍 గ్రామం: {temp_job['area']}\n"
                f"💰 రోజువారీ జీతం: ₹{temp_job['wage']}\n\n"
                "👥 కార్మికులు త్వరలో మీకు కనెక్ట్ అవుతారు.\n"
                "⏳ *గమనిక:* ఈ పని 24 గంటల వరకు మాత్రమే కనిపిస్తుంది.\n\n"
                "📞 వెంటనే కాల్ వచ్చినప్పుడు స్పందించండి – ఖాళీలు త్వరగా నింపబడతాయి.\n\n"
                "ధన్యవాదాలు 🙏\n"
                "– మీ *బ్లూ కనెక్ట్ (Blue Connect)* టీం💙"
            )

        elif incoming == "2":
            # FEATURE 1: Farmer wants to edit - show field selection menu
            users_collection.update_one(
                {"phone": phone},
                {"$set": {"step": "farmer_edit_choice"}}
            )
            msg.body(
                "📝 *ఏ వివరాన్ని సవరించాలనుకుంటున్నారు?*\n\n"
                "1️⃣ 📍 గ్రామం\n"
                "2️⃣ 🌾 పని రకం\n"
                "3️⃣ 💰 జీతం\n"
                "4️⃣ 👥 అవసరమైన లింగం\n"
                "5️⃣ 🔢 కార్మికుల సంఖ్య"
            )
        else:
            msg.body(
                "⚠️ సరైన ఎంపిక ఇవ్వలేదు\n\n"
                "దయచేసి ఎంచుకోండి:\n"
                "1️⃣ ధృవీకరించండి & పోస్ట్ చేయండి\n"
                "2️⃣ వివరాలు సవరించండి"
            )

        return str(resp)

    # FEATURE 1: Handle edit field selection
    if step == "farmer_edit_choice":
        edit_steps = {
            "1": "farmer_edit_village",
            "2": "farmer_edit_work",
            "3": "farmer_edit_wage",
            "4": "farmer_edit_gender",
            "5": "farmer_edit_count"
        }
        
        if incoming not in edit_steps:
            msg.body(
                "⚠️ సరైన ఎంపిక ఇవ్వలేదు\n\n"
                "దయచేసి ఎంచుకోండి:\n"
                "1️⃣ గ్రామం\n"
                "2️⃣ పని రకం\n"
                "3️⃣ జీతం\n"
                "4️⃣ లింగం\n"
                "5️⃣ సంఖ్య"
            )
            return str(resp)
        
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"step": edit_steps[incoming]}}
        )
        
        # Show appropriate prompt based on selection
        if incoming == "1":
            msg.body(
                "📍 గ్రామం ఎంచుకోండి:\n\n" +
                "\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)])
            )
        elif incoming == "2":
            msg.body(
                "🌾 *పని రకం ఎంచుకోండి*\n\n" +
                "\n".join([
                    f"{i+1}. {WORK_TYPE_ICONS[w]} {w}"
                    for i, w in enumerate(WORK_TYPES)
                ])
            )
        elif incoming == "3":
            msg.body("💰 రోజువారీ జీతం నమోదు చేయండి (₹400 – ₹1000)")
        elif incoming == "4":
            msg.body(
                "👥 ఎవరు కావాలి?\n\n"
                "1️⃣👨 పురుషులు\n"
                "2️⃣👩 మహిళలు\n"
                "3️⃣👨🏻‍🤝‍👩🏻 ఇద్దరూ"
            )
        elif incoming == "5":
            msg.body(
                "👥 ఎంత మంది అవసరం?\n\n"
                "👉 సంఖ్య మాత్రమే పంపండి (ఉదా: 5)"
            )
        
        return str(resp)

    # FEATURE 1: Edit flow - village
    if step == "farmer_edit_village":
        if not incoming.isdigit() or not (1 <= int(incoming) <= len(VILLAGES)):
            msg.body("⚠️ సరైన గ్రామ సంఖ్య పంపండి")
            return str(resp)

        user = users_collection.find_one({"phone": phone})
        temp_job = user["temp_job"]
        temp_job["area"] = VILLAGES[int(incoming)-1]

        # FEATURE 1: Display gender in Telugu for acknowledgement
        gender_display = {"male": "పురుషులు", "female": "మహిళలు", "both": "ఇద్దరూ"}

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"temp_job": temp_job, "step": "farmer_confirm"}}
        )

        # FEATURE 1: Show acknowledgement again after editing
        msg.body(
            f"🙏 {user['poster_name']} గారు,\n\n"
            "📋 *మీరు నమోదు చేసిన వివరాలు:*\n\n"
            f"{WORK_TYPE_ICONS[temp_job['work_type']]} పని: {temp_job['work_type']}\n"
            f"📍 గ్రామం: {temp_job['area']}\n"
            f"💰 రోజువారీ జీతం: ₹{temp_job['wage']}\n"
            f"👥 అవసరం: {gender_display[temp_job['gender_required']]}\n"
            f"🔢 సంఖ్య: {temp_job['persons_needed']} మంది\n\n"
            "దయచేసి ఎంచుకోండి:\n\n"
            "1️⃣ ధృవీకరించండి & పోస్ట్ చేయండి\n"
            "2️⃣ వివరాలు సవరించండి"
        )
        return str(resp)

    # FEATURE 1: Edit flow - work type
    if step == "farmer_edit_work":
        if not incoming.isdigit() or not (1 <= int(incoming) <= len(WORK_TYPES)):
            msg.body("⚠️ సరైన పని రకం సంఖ్య పంపండి")
            return str(resp)

        user = users_collection.find_one({"phone": phone})
        temp_job = user["temp_job"]
        temp_job["work_type"] = WORK_TYPES[int(incoming)-1]

        # FEATURE 1: Display gender in Telugu for acknowledgement
        gender_display = {"male": "పురుషులు", "female": "మహిళలు", "both": "ఇద్దరూ"}

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"temp_job": temp_job, "step": "farmer_confirm"}}
        )

        # FEATURE 1: Show acknowledgement again after editing
        msg.body(
            f"🙏 {user['poster_name']} గారు,\n\n"
            "📋 *మీరు నమోదు చేసిన వివరాలు:*\n\n"
            f"{WORK_TYPE_ICONS[temp_job['work_type']]} పని: {temp_job['work_type']}\n"
            f"📍 గ్రామం: {temp_job['area']}\n"
            f"💰 రోజువారీ జీతం: ₹{temp_job['wage']}\n"
            f"👥 అవసరం: {gender_display[temp_job['gender_required']]}\n"
            f"🔢 సంఖ్య: {temp_job['persons_needed']} మంది\n\n"
            "దయచేసి ఎంచుకోండి:\n\n"
            "1️⃣ ధృవీకరించండి & పోస్ట్ చేయండి\n"
            "2️⃣ వివరాలు సవరించండి"
        )
        return str(resp)

    # FEATURE 1: Edit flow - wage
    if step == "farmer_edit_wage":
        if not incoming.isdigit() or not (400 <= int(incoming) <= 1000):
            msg.body("⚠️ జీతం ₹400 నుండి ₹1000 మధ్య ఉండాలి")
            return str(resp)

        user = users_collection.find_one({"phone": phone})
        temp_job = user["temp_job"]
        temp_job["wage"] = int(incoming)

        # FEATURE 1: Display gender in Telugu for acknowledgement
        gender_display = {"male": "పురుషులు", "female": "మహిళలు", "both": "ఇద్దరూ"}

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"temp_job": temp_job, "step": "farmer_confirm"}}
        )

        # FEATURE 1: Show acknowledgement again after editing
        msg.body(
            f"🙏 {user['poster_name']} గారు,\n\n"
            "📋 *మీరు నమోదు చేసిన వివరాలు:*\n\n"
            f"{WORK_TYPE_ICONS[temp_job['work_type']]} పని: {temp_job['work_type']}\n"
            f"📍 గ్రామం: {temp_job['area']}\n"
            f"💰 రోజువారీ జీతం: ₹{temp_job['wage']}\n"
            f"👥 అవసరం: {gender_display[temp_job['gender_required']]}\n"
            f"🔢 సంఖ్య: {temp_job['persons_needed']} మంది\n\n"
            "దయచేసి ఎంచుకోండి:\n\n"
            "1️⃣ ధృవీకరించండి & పోస్ట్ చేయండి\n"
            "2️⃣ వివరాలు సవరించండి"
        )
        return str(resp)

    # FEATURE 1: Edit flow - gender
    if step == "farmer_edit_gender":
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

        user = users_collection.find_one({"phone": phone})
        temp_job = user["temp_job"]
        temp_job["gender_required"] = gender_map[incoming]

        # FEATURE 1: Display gender in Telugu for acknowledgement
        gender_display = {"male": "పురుషులు", "female": "మహిళలు", "both": "ఇద్దరూ"}

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"temp_job": temp_job, "step": "farmer_confirm"}}
        )

        # FEATURE 1: Show acknowledgement again after editing
        msg.body(
            f"🙏 {user['poster_name']} గారు,\n\n"
            "📋 *మీరు నమోదు చేసిన వివరాలు:*\n\n"
            f"{WORK_TYPE_ICONS[temp_job['work_type']]} పని: {temp_job['work_type']}\n"
            f"📍 గ్రామం: {temp_job['area']}\n"
            f"💰 రోజువారీ జీతం: ₹{temp_job['wage']}\n"
            f"👥 అవసరం: {gender_display[temp_job['gender_required']]}\n"
            f"🔢 సంఖ్య: {temp_job['persons_needed']} మంది\n\n"
            "దయచేసి ఎంచుకోండి:\n\n"
            "1️⃣ ధృవీకరించండి & పోస్ట్ చేయండి\n"
            "2️⃣ వివరాలు సవరించండి"
        )
        return str(resp)

    # FEATURE 1: Edit flow - count (then show acknowledgement again)
    if step == "farmer_edit_count":
        if not incoming.isdigit():
            msg.body(
                "⚠️ సరైన సంఖ్య పంపండి\n"
                "(ఉదా: 5)"
            )
            return str(resp)

        user = users_collection.find_one({"phone": phone})
        temp_job = user["temp_job"]
        temp_job["persons_needed"] = int(incoming)

        # FEATURE 1: Display gender in Telugu for acknowledgement
        gender_display = {"male": "పురుషులు", "female": "మహిళలు", "both": "ఇద్దరూ"}

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"temp_job": temp_job, "step": "farmer_confirm"}}
        )

        # FEATURE 1: Show acknowledgement again after editing
        msg.body(
            f"🙏 {user['poster_name']} గారు,\n\n"
            "📋 *మీరు నమోదు చేసిన వివరాలు:*\n\n"
            f"{WORK_TYPE_ICONS[temp_job['work_type']]} పని: {temp_job['work_type']}\n"
            f"📍 గ్రామం: {temp_job['area']}\n"
            f"💰 రోజువారీ జీతం: ₹{temp_job['wage']}\n"
            f"👥 అవసరం: {gender_display[temp_job['gender_required']]}\n"
            f"🔢 సంఖ్య: {temp_job['persons_needed']} మంది\n\n"
            "దయచేసి ఎంచుకోండి:\n\n"
            "1️⃣ ధృవీకరించండి & పోస్ట్ చేయండి\n"
            "2️⃣ వివరాలు సవరించండి"
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
                "1️⃣ నేను రైతుని (పని ఇవ్వాలి)\n"
                "2️⃣ నేను కార్మికుని (పని కావాలి)"
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

        # FEATURE 2: Send notification to farmer when worker applies
        if twilio_client:
            try:
                worker_gender_display = "పురుషుడు" if user["gender"] == "male" else "మహిళ"
                farmer_notification = (
                    f"🔔 *కొత్త అప్లికేషన్ వచ్చింది!*\n\n"
                    f"📋 పని: {job['work_type']}\n"
                    f"📍 గ్రామం: {job['area']}\n"
                    f"💰 జీతం: ₹{job['wage']}\n\n"
                    f"👤 కార్మికుడు వివరాలు:\n"
                    f"📞 ఫోన్: {phone}\n"
                    f"👥 లింగం: {worker_gender_display}\n\n"
                    f"దయచేసి వారిని సంప్రదించండి."
                )
                twilio_client.messages.create(
                    from_=TWILIO_WHATSAPP_NUMBER,
                    body=farmer_notification,
                    to=job["contact"]
                )
            except Exception as e:
                # Silent fail - don't block worker flow
                print(f"Failed to send farmer notification: {e}")

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
