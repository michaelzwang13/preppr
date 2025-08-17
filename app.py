from src import create_app
from flask import jsonify

# Create the application instance using the factory
app = create_app()

if __name__ == '__main__':
    # app.run(host='127.0.0.1', port=5001, debug=True)
    
    # The host must be set to '0.0.0.0' to be accessible from outside the container
    # if you are using Docker
    app.run(host="0.0.0.0", port=8080, debug=True)
