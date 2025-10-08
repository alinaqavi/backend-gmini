import os
import base64
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
# Note: You will need to add the fitz and PIL imports back 
# for PDF support, but they are not strictly needed to fix this NameError.

# ---------------- Flask App config ----------------
# FIX 1: Changed _name_ to __name__
app = Flask(__name__)
CORS(app)

# ---------------- Gemini API config ----------------
# FIX 2: Load API Key securely from the environment. 
# REMEMBER to set GEMINI_API_KEY in your system environment variables!
API_KEY = os.environ.get("GEMINI_API_KEY") 
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key="

if not API_KEY:
    print("FATAL ERROR: GEMINI_API_KEY environment variable not set. API calls will fail.")
    # For local testing, you can uncomment and replace with your key:
    # API_KEY = "YOUR_FALLBACK_KEY_HERE"

# --- Map product IDs to local static images (UNCHANGED) ---
PRODUCT_MAP = {
    "cup": "static/cup.png",
    "bag": "static/bag.jpeg",
    "paper_bowl": "static/paper_bowl.jpg",
    "meal_box": "static/meal_box.png",
    "wrapping_paper": "static/wrapping_paper.jpg",
    "napkin": "static/napkin.webp",
}

# Generic Gemini prompt for initial mockups (UNCHANGED)
GENERIC_PROMPT = (
    "Blend the logo onto this product. Ensure the logo is integrated realistically with proper "
    "lighting, shadows, and texture. Add minimal design yourself according to the product and logo around "
    "the logo on whole product. "
    "Generate a high-quality image of the product with a simple,set prduct color if it is nessacry,according to logo n "
    " clean background that does not distract from the product. Ensure the focus is entirely on the product, with soft lighting and realistic shadows, making it visually appealing and professional. "
)

# Product-specific prompts (Kept for completeness) (UNCHANGED)
PRODUCT_PROMPTS = {
    "cup": "Generate a high-quality photo of a paper coffee cup with this logo on it, featuring soft studio lighting and a clean background.",
    "bag": "Make a mockup of a paper bag with overlay of given logo. It should look realistic and the logo should look big according to the bag. Make whole bag according to logo background and do styling in whole bag.",
    "paper_bowl": "Render a clear, top-down photo of a paper food bowl with this logo on the side. The scene should be set in a bright, modern cafe.",
    "meal_box": "Generate a high-quality photo of a meal box with this logo on it,featuring soft studio lighting and a clean background ,realistic look ",
    "wrapping_paper":"Create a seamless repeating pattern design with a small elegant logo, evenly distributed across the entire surface. The logo should be clean, minimal, and professional, suitable for premium product packaging (like tissues, cups, or paper bags). The design should have subtle spacing so the pattern looks balanced and high-end, similar to luxury brand prints. No background color, only the logo pattern in a single embossed style.",
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
        # ⚠ Note: This version assumes you'll re-integrate the full PDF logic 
        # that correctly determines or converts the logo's mime type (image/png or image/jpeg).
        # For now, we'll use the one passed from the frontend.
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
        
        # Determine product image MIME type (assuming based on file extension)
        product_mime_type = "image/jpeg" 
        if product_image_path.endswith(".webp"):
            product_mime_type = "image/webp"
        elif product_image_path.endswith(".png"):
            product_mime_type = "image/png"


        # Construct the final prompt: User prompt overrides/prepends generic one
        final_prompt = f"{user_design_prompt}. {GENERIC_PROMPT}" if user_design_prompt else GENERIC_PROMPT

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
        # API_KEY is loaded from environment variable
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


# FIX 1: Changed _name_ to __name__
if __name__ == "__main__": 
    app.run(host="0.0.0.0", port=8080, debug=True)
