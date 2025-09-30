import os
import requests
import base64
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
# Initialize the Flask application
load_dotenv()  # .env file read kare

# Get API key from environment
API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Flask app
app = Flask(__name__)
CORS(app)
# Use the correct API URL for the image generation model.
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key="

# --- Mockup Configuration ---
# Map product keys to the static image file paths.
# ASSUMING RENAME WAS DONE: wrapping_paper.jpg
PRODUCT_MAP = {
    "cup": "static/cup.png", 
    "meal_box": "static/meal box.png", 
    "napkin": "static/napkin.webp",
    "paper_bowl": "static/paper_bowl.jpg",
    "bag": "static/bag.jpeg", 
    "wrapping papper": "static/wrapping papper.jpg",
}

# --- Custom Prompt Definitions (Finalized Design Logic) ---
PRODUCT_PROMPTS = {
    # 1. Paper Bag (Full Packaging Design)
    "bag": "Generate a full, highly realistic packaging design studio mockup. Integrate the **uploaded logo** as a large, primary graphic on the center-front face of the standing paper shopping bag. **Generate and apply complementary design elements, lines, or subtle repeating patterns** based on the style of the uploaded logo and the product's function, across the visible surface areas of the bag to create a complete, branded look. **Strictly maintain the original product image's base color, texture, and background environment.** The logo and design must be applied with realistic lighting and shadows.",

    # 2. Wrapping Paper (All-Over Repeating Pattern)
   "wrapping papper": "A photorealistic, top-down view of wrapping paper. Apply the **uploaded logo** as a seamless, repetitive, all-over pattern covering the entire paper. Preserve the paper's original texture, lighting, and background environment.",
    # 3. Paper Napkin (SINGLE, CENTRAL Logo)
    "napkin": "A highly realistic, top-down studio photograph of a neatly stacked pile of white paper napkins. Place the **uploaded logo** as a **single, prominent graphic positioned perfectly in the center** of the top napkin of the stack. The logo should conform realistically to the subtle texture and slight imperfections of the napkin, with natural shadows and lighting. **Maintain the original color of the napkins and the background environment** of the mockup.",

    # 4. Meal Box (Full Packaging Design)
    "meal_box": "Generate a full, highly realistic takeout packaging design studio mockup. Integrate the **uploaded logo** as a large, primary graphic centered on the top lid of the meal box. **Generate and apply complementary branding elements, graphic lines, or subtle repeating patterns** onto the side panels of the box, inspired by the style of the logo or the product's function, to create a complete, branded look. **Strictly maintain the original base colors and materials of the meal box**. The design must be realistically applied with texture, lighting, and shadows. The background environment of the mockup should remain unchanged.",

    # 5. Paper Bowl (Full Packaging Design)
    "paper_bowl": "Generate a full, highly realistic disposable packaging design studio mockup. Integrate the **uploaded logo** as a large, primary graphic on the exterior side of the paper bowl, conforming realistically to its curved surface. **Generate and apply complementary design elements or graphic patterns** around the main logo or on the rest of the bowl's exterior, inspired by the logo's style, to create a complete, branded look. **Strictly maintain the original base color and material texture of the bowl**. The design must show appropriate lighting and shadows. The background environment of the mockup should remain consistent with the base product image.",

    # 6. Cup (Full Packaging Design)
    "cup": "Generate a full, highly realistic disposable beverage packaging design studio mockup. Integrate the **uploaded logo** as a large, primary graphic centered on the front face of the cup. **Generate and apply complementary design elements, patterns, or graphic lines** onto the cup's surface, inspired by the logo's style, to complete the branded look. The design should conform realistically to the curved surface, displaying natural lighting, shadows, and subtle texture, while **strictly preserving the original base color of the cup and the background environment** of the mockup."
}

# --- Backend Endpoint ---
@app.route("/generate-mockup-gemini", methods=["POST"])
def generate_mockup_gemini():
    """
    Receives a JSON payload with a product name and a Base64-encoded logo,
    sends them to the Gemini API for image generation, and returns the result.
    """
    try:
        data = request.get_json()
        product_name = data.get("product_name")
        logo_b64 = data.get("logo_b64")

        if not product_name or not logo_b64:
            return jsonify({"error": "Missing product name or logo file in request body"}), 400

        # Retrieve the specific, style-driven prompt for the chosen product
        prompt = PRODUCT_PROMPTS.get(product_name)
        if not prompt:
            return jsonify({"error": f"No custom prompt found for product: {product_name}"}), 400

        # Get the static image file path

        product_image_path = PRODUCT_MAP.get(product_name)
        # --- NEW: Integrate optional extra_text from frontend ---
        extra_text = data.get("extra_text", "").strip()  # frontend se aaya hua optional instructions
        if extra_text:
         prompt = f"{prompt} {extra_text}"  # Merge with existing product prompt
    
        
        if not product_image_path:
            return jsonify({"error": "Invalid product name or product image path missing"}), 400

        # Read the static product image and convert to Base64
        try:
            with open(product_image_path, "rb") as image_file:
                # Determine MIME type based on file extension
                file_extension = product_image_path.lower()
                if file_extension.endswith(('.jpg', '.jpeg')):
                    mime_type = "image/jpeg"
                elif file_extension.endswith('.webp'):
                    mime_type = "image/webp"
                elif file_extension.endswith('.png'):
                    mime_type = "image/png"
                else:
                    mime_type = "image/jpeg" # Default fallback 

                product_b64 = base64.b64encode(image_file.read()).decode("utf-8")
        except FileNotFoundError:
            # SPECIFIC ERROR FOR FILE PATH ISSUES
            print(f"❌ File Not Found Error: The file at path '{product_image_path}' could not be found.")
            return jsonify({"error": f"File Not Found: Please ensure '{product_image_path}' exists and is named correctly (check for spaces or typos!)"}), 500


        # Construct the Gemini API payload with BOTH images and the custom prompt
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},  # Use the specific product prompt
                        {
                            "inlineData": {
                                "mimeType": mime_type, 
                                "data": product_b64
                            }
                        },
                        {
                            "inlineData": {
                                "mimeType": "image/png", 
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

        # Make the API call
        headers = {"Content-Type": "application/json"}
        response = requests.post(f"{API_URL}{API_KEY}", json=payload, headers=headers)
        response.raise_for_status() 

        # Extract the Base64-encoded image from the response
        result = response.json()
        img_b64 = result.get("candidates")[0]["content"]["parts"][0]["inlineData"]["data"]

        # Return the Base64-encoded image to the frontend
        return jsonify({
            "image_b64": img_b64,
            "message": "Mockup generated successfully!"
        })

    except requests.exceptions.RequestException as e:
        print("❌ API request failed:", e)
        try:
            error_details = e.response.json()
            error_message = error_details.get("error", {}).get("message", str(e))
        except:
            error_message = str(e)
            
        return jsonify({"error": f"API request failed: {error_message}"}), 500
    except Exception as e:
        print("❌ Backend error (General):", e)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# --- Route for Frontend ---
@app.route("/")
def home():
    """Serves the frontend HTML page."""
    # This assumes 'templates/index.html' exists with the frontend code
    return render_template("index.html")

# --- Start the server ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
