import os
import io
import base64
import tempfile
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# ===== 1. API Key Load Karein =====
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY .env file mein nahi mili!")

genai.configure(api_key=API_KEY)

# ===== 2. Flask App Banayen =====
app = Flask(__name__)
app.secret_key = "koi-bhi-random-secret-string-yahan"

# File size limit: 20MB (Gemini ki limit)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

# ===== 3. Gemini Model Setup =====
model = genai.GenerativeModel('gemini-3.5-flash-lite')

# Allowed file types
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/heic'}
ALLOWED_DOC_TYPES = {'text/plain', 'text/csv', 'text/markdown'}


# ===== 4. Home Page Route =====
@app.route("/")
def home():
    return render_template("index.html")


# ===== 5. Chat API Route (File Upload Support) =====
@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_msg = request.form.get("message", "").strip()
        file = request.files.get("file")
        
        if not user_msg and not file:
            return jsonify({"error": "Khali message aur file dono nahi bhej sakte"}), 400
        
        # Session history
        if "history" not in session:
            session["history"] = []
        
        # Contents jo Gemini ko bhejen
        contents = []
        
        # File process karein
        if file and file.filename:
            mime_type = file.mimetype
            file_bytes = file.read()
            
            # Image file
            if mime_type in ALLOWED_IMAGE_TYPES:
                try:
                    image = Image.open(io.BytesIO(file_bytes))
                    contents.append(image)
                except Exception as e:
                    return jsonify({"error": f"Image padhne mein masla: {str(e)}"}), 400
            
            # PDF file
            elif mime_type == 'application/pdf':
                temp_path = None
                try:
                    # tempfile module use karein (safe tareeqa)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                        temp_file.write(file_bytes)
                        temp_path = temp_file.name
                    
                    # Gemini ko upload karein
                    uploaded_file = genai.upload_file(temp_path, mime_type="application/pdf")
                    contents.append(uploaded_file)
                    
                except Exception as e:
                    return jsonify({"error": f"PDF padhne mein masla: {str(e)}"}), 400
                finally:
                    # Clean up - file delete karein
                    if temp_path:
                        try:
                            os.remove(temp_path)
                        except:
                            pass
            
            # Text files
            elif mime_type in ALLOWED_DOC_TYPES:
                try:
                    text_content = file_bytes.decode('utf-8', errors='ignore')
                    contents.append(f"[File: {file.filename}]\n\n{text_content}")
                except Exception as e:
                    return jsonify({"error": f"File padhne mein masla: {str(e)}"}), 400
            
            else:
                return jsonify({"error": f"Ye file type supported nahi: {mime_type}"}), 400
        
        # Text message add karein
        if user_msg:
            contents.append(user_msg)
        elif file:
            contents.append("Is file ko analyze karke batao isme kya hai.")
        
        # Gemini chat session
        chat_session = model.start_chat(history=session["history"])
        response = chat_session.send_message(contents)
        
        # History update karein (sirf text, files nahi)
        session["history"] = [
            {
                "role": h.role,
                "parts": [p.text for p in h.parts if hasattr(p, 'text') and p.text]
            }
            for h in chat_session.history
            if any(hasattr(p, 'text') and p.text for p in h.parts)
        ]
        session.modified = True
        
        return jsonify({"reply": response.text})
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500


# ===== 6. Chat Clear Route =====
@app.route("/clear", methods=["POST"])
def clear():
    session.pop("history", None)
    return jsonify({"status": "cleared"})


# ===== 7. App Run Karein =====
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)