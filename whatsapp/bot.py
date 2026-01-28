from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse
from database.db import jobs_collection, users_collection

whatsapp_bp = Blueprint("whatsapp", __name__)

# ---- Helper functions ----

def is_greeting(text):
    greetings = [
        "hi", "hello", "hai",
        "namaste", "namaskaram",
        "నమస్తే", "నమస్కారం",
        "ram", "రామ్"
    ]
    text = text.lower()
    return any(greet in text for greet in greetings)


def is_number(text):
    return text.isdigit()


def is_farmer_choice(text):
    farmer_keywords = ["1", "పని ఇవ్వాలి", "ఇవ్వాలి", "farmer"]
    return any(k in text for k in farmer_keywords)


def is_worker_choice(text):
    worker_keywords = ["2", "పని కావాలి", "కావాలి", "worker"]
    return any(k in text for k in worker_keywords)


# ---- WhatsApp Route ----

@whatsapp_bp.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    incoming_msg = request.values.get("Body", "").strip()
    phone = request.values.get("From")

    resp = MessagingResponse()
    msg = resp.message()

    user = users_collection.find_one({"phone": phone})

    # ---- NEW USER OR GREETING ----
    if not user or is_greeting(incoming_msg):
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"phone": phone, "step": "menu"}},
            upsert=True
        )
        msg.body(
            "🙏 Blue Connect కు స్వాగతం\n\n"
            "మీరు ఏం చేయాలనుకుంటున్నారు?\n\n"
            "1️⃣ పని ఇవ్వాలి\n"
            "2️⃣ పని కావాలి\n\n"
            "1 లేదా 2 పంపండి (లేదా తెలుగులో టైప్ చేయండి)"
        )
        return str(resp)

    # ---- MENU STEP ----
    if user["step"] == "menu":
        if is_farmer_choice(incoming_msg):
            users_collection.update_one(
                {"phone": phone},
                {"$set": {"step": "farmer_area"}}
            )
            msg.body("📍 మీ గ్రామం / ప్రాంతం పేరు నమోదు చేయండి (తెలుగు లేదా ఇంగ్లీష్)")
        elif is_worker_choice(incoming_msg):
            users_collection.update_one(
                {"phone": phone},
                {"$set": {"step": "worker_area"}}
            )
            msg.body("📍 మీరు పని చేయాలనుకున్న గ్రామం పేరు నమోదు చేయండి")
        else:
            msg.body("❗ దయచేసి 1 లేదా 2 పంపండి\n(పని ఇవ్వాలి / పని కావాలి)")
        return str(resp)

    # ---- FARMER: AREA ----
    if user["step"] == "farmer_area":
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"area": incoming_msg, "step": "work_type"}}
        )
        msg.body(
            "🧑‍🌾 పని రకం ఏమిటి?\n\n"
            "ఉదాహరణలు:\n"
            "- కోత\n"
            "- నాట్లు\n"
            "- పిచికారీ\n"
            "- తోట పని"
        )
        return str(resp)

    # ---- FARMER: WORK TYPE ----
    if user["step"] == "work_type":
        users_collection.update_one(
            {"phone": phone},
            {"$set": {"work_type": incoming_msg, "step": "wage"}}
        )
        msg.body("💰 రోజువారీ జీతం ఎంత? (సంఖ్యలో నమోదు చేయండి – ఉదా: 600)")
        return str(resp)

    # ---- FARMER: WAGE ----
    if user["step"] == "wage":
        if not is_number(incoming_msg):
            msg.body("❌ దయచేసి సరైన సంఖ్య నమోదు చేయండి\nఉదా: 600")
            return str(resp)

        wage = int(incoming_msg)

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"wage": wage}}
        )

        user = users_collection.find_one({"phone": phone})

        jobs_collection.insert_one({
            "area": user["area"],
            "work_type": user["work_type"],
            "wage": wage,
            "contact": phone
        })

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"step": "menu"}}
        )

        msg.body(
            "✅ మీ పని వివరాలు సేవ్ అయ్యాయి 🙏\n\n"
            "గ్రామం: {0}\n"
            "పని: {1}\n"
            "జీతం: ₹{2}\n\n"
            "మరల ప్రారంభించడానికి Hi పంపండి"
            .format(user["area"], user["work_type"], wage)
        )
        return str(resp)

    # ---- WORKER: AREA ----
    if user["step"] == "worker_area":
        jobs = jobs_collection.find({"area": incoming_msg})

        reply = ""
        for job in jobs:
            reply += (
                f"🌾 పని: {job['work_type']}\n"
                f"💰 జీతం: ₹{job['wage']}\n"
                f"📞 సంప్రదించండి: {job['contact']}\n\n"
            )

        if reply == "":
            reply = (
                "❌ ఈ ప్రాంతంలో ప్రస్తుతం పనులు లేవు\n\n"
                "మరల ప్రయత్నించడానికి Hi పంపండి"
            )

        users_collection.update_one(
            {"phone": phone},
            {"$set": {"step": "menu"}}
        )

        msg.body(reply)
        return str(resp)

    # ---- FALLBACK ----
    msg.body("❓ అర్థం కాలేదు. మళ్లీ ప్రారంభించడానికి Hi పంపండి")
    return str(resp)
