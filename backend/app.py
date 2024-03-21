from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import requests
import os
from config import API_USER_TOKEN

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
API_USER_TOKEN = API_USER_TOKEN

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload-image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image part'}), 400
    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': 'Invalid image'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Send image to LogMeal API for ingredient recognition
    headers = {'Authorization': f'Bearer {API_USER_TOKEN}'}

    # Single/Several Dishes Detection
    with open(filepath, 'rb') as img:
        response = requests.post(
            'https://api.logmeal.es/v2/image/segmentation/complete',
            files={'image': img},
            headers=headers
        )

    if response.status_code == 200:
        image_id = response.json()['imageId']

        # Ingredients information
        ingredients_response = requests.post(
            'https://api.logmeal.es/v2/recipe/ingredients',
            json={'imageId': image_id},
            headers=headers
        )

        if ingredients_response.status_code == 200:
            # Send the image with highlighted ingredients and the ingredients info back to the client
            return jsonify({
                'imageUrl': request.host_url + 'uploads/' + filename,
                'ingredients': ingredients_response.json()
            })
        else:
            return jsonify({'error': 'Ingredients recognition failed'}), 500
    else:
        return jsonify({'error': 'Dish recognition failed'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True, host='0.0.0.0', port=5000)