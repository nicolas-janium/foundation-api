from foundation_api import create_app
import os
from dotenv import load_dotenv
import foundation_api.V1.utils.demoji_module as demoji

load_dotenv()

if __name__ == "__main__":
    # print(os.getenv('FLASK_HOST'))
    app = create_app()
    app.run(host=os.getenv('FLASK_HOST', '127.0.0.1'), debug=True, use_reloader=False)
