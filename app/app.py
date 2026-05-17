from flask import Flask  # Importing the Flask module from the flask package  
 
app = Flask(__name__)

@app.route('/')  # View function for endpoint '/'  
def hello():  
    return "<h1>Hello, World!</h1>"
if __name__ == "__main__":  
    app.run(host='0.0.0.0', port=5000, debug=True)