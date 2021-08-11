import os
from functools import wraps


from flask import Flask, request, jsonify, make_response
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_sendgrid import SendGrid
from flask_cors import CORS


bcrypt = Bcrypt()
jwt = JWTManager()
mail = SendGrid()
cors = CORS()

def create_app(test_config=False):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    if not test_config:
        app.config.from_object('config')
    else:
        app.config.from_object('test_config')

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    ### Extensions and stuff ###
    ###                      ###
    from foundation_api.V1.sa_db.model import db
    db.init_app(app)

    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    cors.init_app(app)

    from foundation_api.V1.mod_auth.routes import mod_auth as auth_module
    from foundation_api.V1.mod_campaign.routes import mod_campaign as campaign_module
    from foundation_api.V1.mod_home.routes import mod_home as home_module
    from foundation_api.V1.mod_onboard.routes import mod_onboard as onboard_module
    from foundation_api.V1.mod_jobs.routes import mod_jobs as jobs_module
    # from foundation_api.V1.mod_email.routes import mod_email as email_module
    from foundation_api.V1.mod_tasks.routes import mod_tasks as tasks_module
    from foundation_api.V1.mod_ulinc.routes import mod_ulinc as ulinc_module


    # Register blueprint(s)
    app.register_blueprint(auth_module)
    app.register_blueprint(campaign_module)
    app.register_blueprint(home_module)
    app.register_blueprint(onboard_module)
    app.register_blueprint(jobs_module)
    # app.register_blueprint(email_module)
    app.register_blueprint(tasks_module)
    app.register_blueprint(ulinc_module)

    return app

def check_json_header(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if str(request.headers.get('Content-Type')).lower() == 'application/json':
            return f(*args, **kwargs)
        return make_response(jsonify({"message": "Set Content-Type header value to 'application/json'"}), 400)
    return decorated






# ### Old way ###
# # Define the WSGI application object
# app = Flask(__name__)
    
# CORS(app)


# # Configurations
# app.config.from_object('config')

# # Define the database object which is imported
# # by modules and controllers
# app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://nicolas:nicolas113112@localhost/dev"
# # db = SQLAlchemy(app)
# # db.create_all()

# # csrf = CSRFProtect(app)
# # @app.after_request
# # def set_csrf_token(response):
# #     response.set_cookie('csrf_token', generate_csrf())
# #     return response

# jwt = JWTManager(app)
# bcrypt = Bcrypt(app)

# mail = SendGrid(app)

# from foundation_api.V1.mod_auth.routes import mod_auth as auth_module
# from foundation_api.V1.mod_campaign.routes import mod_campaign as campaign_module
# from foundation_api.V1.mod_home.routes import mod_home as home_module
# from foundation_api.V1.mod_onboard.routes import mod_onboard as onboard_module
# from foundation_api.V1.mod_jobs.routes import mod_jobs as jobs_module
# from foundation_api.V1.mod_email.routes import mod_email as email_module
# from foundation_api.V1.mod_tasks.routes import mod_tasks as tasks_module


# # Register blueprint(s)
# app.register_blueprint(auth_module)
# app.register_blueprint(onboard_module)
# app.register_blueprint(home_module)
# app.register_blueprint(campaign_module)
# app.register_blueprint(jobs_module)
# app.register_blueprint(tasks_module)
# app.register_blueprint(email_module)