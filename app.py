import os
import base64
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- Gemini API configuration ---
# NOTE: Replace with your actual key (the one you provided is visible here)
API_KEY = "AIzaSyDlfEh91yCnZQlt1Q8bq28ShEmxgkb_MRI"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key="

# --- Map product IDs to local static images (UNCHANGED) ---
PRODUCT_MAP = {
    "cup": "static/Cup.png", 
    "bag": "static/Bag.jpeg", 
    "paper_bowl": "static/paper_bowl.jpg",
    "meal_box":"static/meal_box.png",
    "wrapping_paper":"static/wrapping_paper.jpg", 
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

PRODUCT_PROMPTS = {
    # 1. Paper Bag (Full Packaging Design)
    "bag": "Generate a full, highly realistic packaging design studio mockup. Integrate the **uploaded logo** as a large, primary graphic on the center-front face of the standing paper shopping bag. **Generate and apply complementary design elements, lines, or subtle repeating patterns** based on the style of the uploaded logo and the product's function, across the visible surface areas of the bag to create a complete, branded look. **Strictly maintain the original product image's base color, texture, and background environment.** The logo and design must be applied with realistic lighting and shadows.",

    # 2. Wrapping Paper (All-Over Repeating Pattern)
   "wrapping_papper": "A photorealistic, top-down view of wrapping paper. Apply the **uploaded logo** as a seamless, repetitive, all-over pattern covering the entire paper. Preserve the paper's original texture, lighting, and background environment.",
    # 3. Paper Napkin (SINGLE, CENTRAL Logo)
    "napkin": "A highly realistic, top-down studio photograph of a neatly stacked pile of white paper napkins. Place the **uploaded logo** as a **single, prominent graphic positioned perfectly in the center** of the top napkin of the stack. The logo should conform realistically to the subtle texture and slight imperfections of the napkin, with natural shadows and lighting. **Maintain the original color of the napkins and the background environment** of the mockup.",

    # 4. Meal Box (Full Packaging Design)
    "meal_box": "Generate a full, highly realistic takeout packaging design studio mockup. Integrate the **uploaded logo** as a large, primary graphic centered on the top lid of the meal box. **Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns** onto the side panels of the box, inspired by the style of the logo or the product's function, to create a complete, branded look. **Strictly maintain the original base colors and materials of the meal box**. The design must be realistically applied with texture, lighting, and shadows. The background environment of the mockup should remain unchanged.",

    # 5. Paper Bowl (Full Packaging Design)
    "paper_bowl": "Generate a full, highly realistic disposable packaging design studio mockup. Integrate the **uploaded logo** as a large, primary graphic on the exterior side of the paper bowl, conforming realistically to its curved surface. **Generate and apply complementary design elements or graphic patterns** around the main logo or on the rest of the bowl's exterior, inspired by the logo's style, to create a complete, branded look. **Strictly maintain the original base color and material texture of the bowl**. The design must show appropriate lighting and shadows. The background environment of the mockup should remain consistent with the base product image.",

    # 6. Cup (Full Packaging Design)
    "cup": "Generate a full, highly realistic disposable beverage packaging design studio mockup. Integrate the **uploaded logo** as a large, primary graphic centered on the front face of the cup. **Generate and apply complementary design elements, patterns, or graphic lines** onto the cup's surface, inspired by the logo's style, to complete the branded look. The design should conform realistically to the curved surface, displaying natural lighting, shadows, and subtle texture, while **strictly preserving the original base color of the cup and the background environment** of the mockup."
}


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate-mockup", methods=["POST"])
def generate_mockup():
    try:
        data = request.get_json()
        product_name = data.get("product_name")
        logo_b64 = data.get("logo_b64")
        # ⚠️ NEW: Get the MIME type from the frontend for ANY file upload
        logo_mime_type = data.get("logo_mime_type", "image/png") 
        user_design_prompt = data.get("design_prompt", "").strip()

        if not product_name or not logo_b64:
            return jsonify({"error": "Missing product name or logo"}), 400

        product_image_path = PRODUCT_MAP.get(product_name)
        if not product_image_path or not os.path.exists(product_image_path):
            return jsonify({"error": f"Product image not found: {product_name}"}), 400

        # Read product image as base64
        with open(product_image_path, "rb") as f:
            product_b64 = base64.b64encode(f.read()).decode("utf-8")
        
        # Determine product image MIME type (assuming based on file extension)
        # We need this to be accurate, so let's check the path extension
        product_mime_type = "image/jpeg" # Default to JPEG, but check for webp and png
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
                        {"text": final_prompt},  # Use the combined or generic prompt
                        {
                            "inlineData": {
                                # ⚠️ IMPORTANT: Use the determined product MIME type
                                "mimeType": product_mime_type, 
                                "data": product_b64
                            }
                        },
                        {
                            "inlineData": {
                                # ⚠️ CRITICAL CHANGE: Use the dynamic MIME type for the logo
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

    except requests.exceptions.RequestException as e:
        print("❌ Gemini API request failed:", e)
        return jsonify({"error": f"API request failed: {e}"}), 500
    except Exception as e:
        print("❌ Backend error:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
