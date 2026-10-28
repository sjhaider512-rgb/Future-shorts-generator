from flask import Flask, render_template, request, jsonify
# Import any other modules you need for your documentary generator (e.g., google-genai, gtts, etc.)

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():
    # If your app has an HTML frontend template, use:
    # return render_template("index.html")
    
    # For now, this baseline ensures your root URL returns a successful response:
    return "Future Shorts Documentary Generator is Live!"

if __name__ == "__main__":
    app.run(debug=True)
