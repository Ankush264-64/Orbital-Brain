import os
from flask import Flask, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# --- CONFIGURATION ---
# 🔑 PASTE YOUR KEY BELOW 🔑
# Replace 'PASTE_YOUR_GEMINI_KEY_HERE' with your real API key "AIza..."
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyA3yUEwN3pDrtxtaeSLy8bOqpvQTtfjp9w")

# Configure Gemini
if GEMINI_KEY == "PASTE_YOUR_GEMINI_KEY_HERE":
    print("⚠️ WARNING: API Key is missing! AI features will not work.")
else:
    genai.configure(api_key=GEMINI_KEY)
    
model = genai.GenerativeModel('gemini-pro')

# --- ROUTES ---

@app.route('/')
def home():
    """The Cool Status Page (What you see in the browser)"""
    return """
    <style>
        body { background-color: #0d0d0d; color: #00d4ff; font-family: 'Courier New', monospace; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .box { border: 2px solid #00d4ff; padding: 40px; text-align: center; box-shadow: 0 0 30px #00d4ff; background-color: rgba(0, 20, 40, 0.8); }
        h1 { margin: 0; font-size: 3rem; text-transform: uppercase; letter-spacing: 5px; text-shadow: 0 0 10px #00d4ff; }
        p { color: #888; margin-top: 15px; font-size: 1.2rem; }
        .blink { animation: blinker 1.5s linear infinite; }
        @keyframes blinker { 50% { opacity: 0; } }
    </style>
    <div class="box">
        <h1>Orbital <span class="blink">●</span> Online</h1>
        <p>System Status: OPERATIONAL</p>
        <p>Cloud Brain: CONNECTED</p>
        <p>Protocol: SECURE</p>
    </div>
    """

@app.route('/command', methods=['POST'])
def process_command():
    """The Logic that talks to your Flutter App"""
    try:
        # 1. Get the text from the phone
        data = request.json
        user_text = data.get('command', '')

        if not user_text:
            return jsonify({"response": "I didn't hear anything, Sir."})

        # 2. THE PERSONALITY (JARVIS MODE)
        system_prompt = (
            "You are Orbital, a futuristic AI assistant for a college student named Ankush. "
            "You are helpful, concise, and slightly witty. "
            "Keep answers short (under 50 words) unless asked for details. "
            "Address him as 'Sir' occasionally."
        )
        full_prompt = f"{system_prompt}\n\nUser: {user_text}"

        # 3. Ask Gemini
        response = model.generate_content(full_prompt)
        reply_text = response.text

        # 4. Send answer back to phone
        return jsonify({"response": reply_text})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"response": "I encountered a system error, Sir."}), 500

if __name__ == '__main__':
    # This allows Render to set the Port dynamically
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
