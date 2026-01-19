import base64
import os 
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask import Flask, render_template
from dotenv import load_dotenv
load_dotenv()
# Note: You will need to add the fitz and PIL imports back 
# for PDF support, but they are not strictly needed to fix this NameError.

# ---------------- Flask App config ----------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# ---------------- Gemini API config ----------------
API_KEY = os.environ.get("GEMINI_API_KEY") 
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key="

if not API_KEY:
    print("FATAL ERROR: GEMINI_API_KEY environment variable not set. API calls will fail.")
    # For local testing, you can uncomment and replace with your key:
    # # API_KEY = "YOUR_FALLBACK_KEY_HERE"

# --- Map product IDs to local static images (UPDATED PATHS) ---
PRODUCT_MAP = {
    "paper_cup": "static/Paper_Cup.jpeg",
    "paper_bag": "static/Paper_Bag.webp",
    "paper_bowl": "static/paper_bowl.jpg",
    "meal_box": "static/meal_box.png",
    "wrapping_paper": "static/wrapping_paper.jpg",
    "paper_napkin": "static/paper_napkin.jpg",
}

# Product-specific prompts
PRODUCT_PROMPTS = {
    # 1. Paper Bag (Full Packaging Design)
    "paper_bag": "Generate a full, highly realistic packaging design studio mockup. Integrate the *uploaded logo* as a large, primary graphic on the center-front face of the standing paper shopping bag. *Generate and apply complementary design elements, lines, or subtle repeating patterns* based on the style of the uploaded logo and the product's function, across the visible surface areas of the bag to create a complete, branded look. *Strictly maintain the original product image's base color, texture, and background environment.* The logo and design must be applied with realistic lighting and shadows.",

    # 2. Wrapping Paper (All-Over Repeating Pattern)
    "wrapping_paper": "Apply the **uploaded logo** as a **small to medium-sized, repeating pattern** across the entire paper surface. The pattern must be **scattered, non-overlapping, and uniformly spaced** to ensure every logo is clean and readable. **Strictly preserve the paper's original color and texture**.",
    # 3. Paper Napkin (SINGLE, CENTRAL Logo)
    "paper_napkin": "A highly realistic, top-down studio photograph of a neatly stacked pile of white paper napkins. Place the *uploaded logo* as a *single, prominent graphic positioned perfectly in the center* of the top napkin of the stack. The logo should conform realistically to the subtle texture and slight imperfections of the napkin, with natural shadows and lighting. *Maintain the original color of the napkins and the background environment* of the mockup.",

    # 4. Meal Box (Full Packaging Design)
    "meal_box": "Generate a full, highly realistic takeout packaging design studio mockup. Integrate the *uploaded logo* as a large, primary graphic centered on the top lid of the meal box. *Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns* onto the side panels of the box, inspired by the style of the logo or the product's function, to create a complete, branded look. *Strictly maintain the original base colors and materials of the meal box*. The design must be realistically applied with texture, lighting, and shadows. The background environment of the mockup should remain unchanged.",

    # 5. Paper Bowl (Full Packaging Design)
    "paper_bowl": "Generate a full, highly realistic disposable packaging design studio mockup. Integrate the *uploaded logo* as a large, primary graphic on the exterior side of the paper bowl, conforming realistically to its curved surface. *Generate and apply complementary design elements or graphic patterns* around the main logo or on the rest of the bowl's exterior, inspired by the logo's style, to create a complete, branded look. *Strictly maintain the original base color and material texture of the bowl*. The design must show appropriate lighting and shadows. The background environment of the mockup should remain consistent with the base product image.",

    # 6. Cup (Full Packaging Design)
    "paper_cup": "Generate a full, highly realistic disposable beverage packaging design studio mockup. Integrate the *uploaded logo* as a large, primary graphic centered on the front face of the cup. *Generate and apply complementary design elements, patterns, or graphic lines* onto the cup's surface, inspired by the logo's style, to complete the branded look. The design should conform realistically to the curved surface, displaying natural lighting, shadows, and subtle texture, while *strictly preserving the original base color of the cup and the background environment* of the mockup."
}

# Allowed file extensions for validation
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.webp', '.bmp', '.tiff'}

def validate_file_type(filename):
    """Validate if the uploaded file has an allowed extension"""
    if not filename:
        return False
    ext = os.path.splitext(filename.lower())[1]
    return ext in ALLOWED_EXTENSIONS
@app.route('/')
def home():
    try:
        return render_template('index.html')
    except Exception as e:
        return f"""
        <h1>Template Error</h1>
        <p>Error: {str(e)}</p>
        <p>Make sure templates/index.html exists in your project.</p>
        """, 500

@app.route("/generate-mockup", methods=["POST"])
def generate_mockup():
    if not API_KEY:
         return jsonify({"error": "Server error: API Key not configured."}), 500
         
    try:
        data = request.get_json()
        product_name = data.get("product_name")
        logo_b64 = data.get("logo_b64")
        logo_mime_type = data.get("logo_mime_type", "image/png")
        logo_filename = data.get("logo_filename", "")
        user_design_prompt = data.get("design_prompt", "").strip()
        brand_name = data.get("brand_name", "").strip()
        color_palette = data.get("color_palette", "").strip()

        # Validate product name
        if not product_name:
            return jsonify({"error": "Missing product name"}), 400
        
        # Validate that either logo OR brand name is provided
        if not logo_b64 and not brand_name:
            return jsonify({"error": "Please provide either a logo file OR a brand name"}), 400
        
        # Validate file type if logo is uploaded
        if logo_b64 and logo_filename:
            if not validate_file_type(logo_filename):
                allowed = ', '.join(ALLOWED_EXTENSIONS)
                return jsonify({"error": f"Invalid file type. Allowed formats: {allowed}"}), 400

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

        # Build the final prompt based on what the user provided
        product_specific_prompt = PRODUCT_PROMPTS.get(product_name, "")
        
        if logo_b64 and brand_name:
            # CONDITION 3: Both logo and brand name
            final_prompt = f"Generate a mockup with BOTH the uploaded logo AND the brand name '{brand_name}'. Place the logo prominently and add the brand name text nearby (e.g., below or beside the logo). {product_specific_prompt}"
        elif logo_b64:
            # CONDITION 2: Logo only
            final_prompt = f"Generate a mockup with ONLY the uploaded logo. {product_specific_prompt}"
        elif brand_name:
            # CONDITION 1: Brand name only (no logo uploaded)
            final_prompt = f"Generate a mockup with ONLY the brand name text '{brand_name}'. Create an attractive text-based design with the brand name prominently displayed. {product_specific_prompt}"
        else:
            return jsonify({"error": "Missing logo or brand name"}), 400
        
        # Add color palette FIRST if provided (so it takes priority)
        if color_palette and color_palette != "None":
            final_prompt = f"Use the color palette: {color_palette}. {final_prompt}"
        
        # Add user's custom design prompt at the BEGINNING (highest priority)
        if user_design_prompt:
            final_prompt = f"{user_design_prompt}. {final_prompt}"
            
        if not final_prompt:
             return jsonify({"error": f"Missing specific prompt for product: {product_name}"}), 400

        # Prepare Gemini API payload
        payload_parts = [{"text": final_prompt}]
        
        # Always add product image
        payload_parts.append({
            "inlineData": {
                "mimeType": product_mime_type, 
                "data": product_b64
            }
        })
        
        # Only add logo image if it was uploaded
        if logo_b64:
            payload_parts.append({
                "inlineData": {
                    "mimeType": logo_mime_type, 
                    "data": logo_b64
                }
            })
        
        payload = {
            "contents": [
                {
                    "parts": payload_parts
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
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
