from src import create_app
import os
import argparse

# Create the application instance using the factory
app = create_app()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run Flask app')
    parser.add_argument('--local', action='store_true', help='Run locally (127.0.0.1:5001)')
    args = parser.parse_args()
    
    # Check for local flag or LOCAL environment variable
    is_local = args.local or os.getenv('LOCAL', 'false').lower() == 'true'
    
    if is_local:
        # Local development
        app.run(host='127.0.0.1', port=5001, debug=True)
    else:
        # Docker/production
        app.run(host="0.0.0.0", port=8080, debug=True)
