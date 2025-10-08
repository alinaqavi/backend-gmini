import os
import base64
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
# Note: You will need to add the fitz and PIL imports back 
# for PDF support, but they are not strictly needed to fix this NameError.

# ---------------- Flask App config ----------------
app = Flask(__name__)
CORS(app)

# ---------------- Gemini API config ----------------
API_KEY = os.environ.get("GEMINI_API_KEY") 
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key="

if not API_KEY:
    print("FATAL ERROR: GEMINI_API_KEY environment variable not set. API calls will fail.")
    # For local testing, you can uncomment and replace with your key:
    # # API_KEY = "YOUR_FALLBACK_KEY_HERE"

# --- Map product IDs to local static images (UNCHANGED) ---
PRODUCT_MAP = {
    "cup": "static/cup.png",
    "bag": "static/bag.jpeg",
    "paper_bowl": "static/paper_bowl.jpg",
    "meal_box": "static/meal_box.png",
    "wrapping_paper": "static/wrapping_paper.jpg",
    "napkin": "static/napkin.webp",
}

# 💥 GENERIC_PROMPT HAS BEEN REMOVED 💥

# Product-specific prompts
PRODUCT_PROMPTS = {
    "cup": "Generate a high-quality photo of a paper coffee cup with this logo on it, featuring soft studio lighting and a clean background.",
    "bag": "Make a mockup of a paper bag with overlay of given logo. It should look realistic and the logo should look big according to the bag. Make whole bag according to logo background and do styling in whole bag.",
    "paper_bowl": "Render a clear, top-down photo of a paper food bowl with this logo on the side. The scene should be set in a bright, modern cafe.",
    "meal_box": "Generate a high-quality photo of a meal box with this logo on it,featuring soft studio lighting and a clean background ,realistic look ",
    "wrapping_paper": "Apply the **uploaded logo** as a **seamless, tight, repeating pattern** covering the entire wrapping paper surface. The pattern should be small and evenly distributed, creating a continuous, branded background effect. Ensure the final look is realistic, maintaining the paper's texture and lighting. **Do not add any single, large, or centered logo.**",
    "paper_napkin": "design according to professinal paper napkin, "
}


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate-mockup", methods=["POST"])
def generate_mockup():
    if not API_KEY:
         return jsonify({"error": "Server error: API Key not configured."}), 500
         
    try:
        data = request.get_json()
        product_name = data.get("product_name")
        logo_b64 = data.get("logo_b64")
        logo_mime_type = data.get("logo_mime_type", "image/png") 
        user_design_prompt = data.get("design_prompt", "").strip()

        if not product_name or not logo_b64:
            return jsonify({"error": "Missing product name or logo"}), 400
        
        # --- (Place the FULL PDF CONVERSION LOGIC HERE later) ---

        product_image_path = PRODUCT_MAP.get(product_name)
        if not product_image_path or not os.path.exists(product_image_path):
            return jsonify({"error": f"Product image not found: {product_name}"}), 400

        # Read product image as base64
        with open(product_image_path, "rb") as f:
            product_b64 = base64.b64encode(f.read()).decode("utf-8")
        
        # Determine product image MIME type
        product_mime_type = "image/jpeg" 
        if product_image_path.endswith(".webp"):
            product_mime_type = "image/webp"
        elif product_image_path.endswith(".png"):
            product_mime_type = "image/png"


        # --- UPDATED PROMPT CONSTRUCTION LOGIC ---
        product_specific_prompt = PRODUCT_PROMPTS.get(product_name, "")
        
        if user_design_prompt:
            final_prompt = f"{user_design_prompt}. {product_specific_prompt}"
        else:
            final_prompt = product_specific_prompt
            
        if not final_prompt:
             return jsonify({"error": f"Missing specific prompt for product: {product_name}"}), 400
        # ----------------------------------------

        # Prepare Gemini API payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": final_prompt}, 
                        {
                            "inlineData": {
                                "mimeType": product_mime_type, 
                                "data": product_b64
                            }
                        },
                        {
                            "inlineData": {
                                "mimeType": logo_mime_type, 
                                "data": logo_b64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["IMAGE"]
            }
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(f"{API_URL}{API_KEY}", json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()

        candidates = result.get("candidates", [])
        if not candidates:
            return jsonify({"error": "No image generated from Gemini"}), 500

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts or "inlineData" not in parts[0]:
            return jsonify({"error": "No inlineData found in Gemini response"}), 500

        img_b64 = parts[0]["inlineData"]["data"]

        return jsonify({"image_b64": img_b64, "message": "Mockup generated successfully!"})

    except requests.exceptions.HTTPError as e:
        print(f"❌ Gemini API HTTP Error: {e.response.status_code} - {e.response.text}")
        return jsonify({"error": f"API request failed with status {e.response.status_code}. Check server logs for details."}), e.response.status_code
    except requests.exceptions.RequestException as e:
        print("❌ Gemini API request failed:", e)
        return jsonify({"error": f"API request failed: {e}"}), 500
    except Exception as e:
        print("❌ Backend error:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__": 
    app.run(host="0.0.0.0", port=8080, debug=True)
