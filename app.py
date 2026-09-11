import os
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
import google.generativeai as genai

# ===== 1. API Key Load Karein =====
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("❌ GEMINI_API_KEY .env file mein nahi mili!")

genai.configure(api_key=API_KEY)

# ===== 2. Flask App Banayen =====
app = Flask(__name__)
app.secret_key = "koi-bhi-random-secret-string-yahan"  # Session ke liye zaroori

# ===== 3. Gemini Model Setup =====
model = genai.GenerativeModel('gemini-3.6-flash')


# ===== 4. Home Page Route =====
@app.route("/")
def home():
    return render_template("index.html")


# ===== 5. Chat API Route =====
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_msg = data.get("message", "").strip()
        
        if not user_msg:
            return jsonify({"error": "Khali message nahi bhej sakte"}), 400
        
        # Session mein chat history store karein
        if "history" not in session:
            session["history"] = []
        
        # Gemini chat session banayen
        chat_session = model.start_chat(history=session["history"])
        
        # Message bhejein
        response = chat_session.send_message(user_msg)
        
        # History update karein (aage ke messages ke liye)
        session["history"] = [
            {
                "role": h.role,
                "parts": [p.text for p in h.parts]
            }
            for h in chat_session.history
        ]
        session.modified = True
        
        return jsonify({"reply": response.text})
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


# ===== 6. App Run Karein =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)