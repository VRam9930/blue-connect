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

WORK_TYPE_ICONS = {
    "నాట్లు": "🌱",
    "కోత": "✂️",
    "పంట తీయడం": "🌾",
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
            "🙏 *Blue Connect కు స్వాగతం*\n\n"
            "మీరు ఏమి చేయాలనుకుంటున్నారు?\n\n"
            "1️⃣ పని ఇవ్వాలంటే – 1 పంపండి\n"
            "2️⃣ పని కావాలంటే – 2 పంపండి"
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
                    "📍 ఈసారి పని ఏ గ్రామంలో చేయాలి?\n\n"
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
                "1️⃣ పురుషుడు\n"
                "2️⃣ మహిళ"
            )
        else:
            msg.body(
                "❓ మళ్లీ ఎంచుకోండి:\n\n"
                "1️⃣ పని ఇవ్వాలంటే – 1 పంపండి\n"
                "2️⃣ పని కావాలంటే – 2 పంపండి"
            )
        return str(resp)

    # ================= FARMER FLOW =================
    if step == "farmer_name":
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"poster_name": incoming, "step": "farmer_poster_gender"}}
        )
        msg.body(" మీ లింగం ఎంచుకోండి:\n1️⃣ పురుషుడ🚹 \n2️⃣ మహిళ 🚺")
        return str(resp)

    if step == "farmer_poster_gender":
        if incoming not in ["1", "2"]:
            msg.body("⚠️ 1 లేదా 2 పంపండి")
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
            "📍 *ఈ పని ఏ గ్రామంలో చేయాలి?*\n\n"
            + "\n".join([f"{i+1}. {v}" for i, v in enumerate(VILLAGES)])
        )
        return str(resp)
