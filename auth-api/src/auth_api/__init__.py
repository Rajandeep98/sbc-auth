# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""The Authroization API service.

This module is the API for the Authroization system.
"""
import os
import traceback

from flask import Flask, request
from flask_cors import CORS
from flask_migrate import Migrate, upgrade
from sbc_common_components.utils.camel_case_response import convert_to_camel

import auth_api.config as config  # pylint:disable=consider-using-from-import
from auth_api.config import _Config
from auth_api.exceptions import ExceptionHandler
from auth_api.extensions import mail
from auth_api.models import db, ma
from auth_api.resources import endpoints
from auth_api.services.flags import flags
from auth_api.services.gcp_queue import queue
from auth_api.utils.auth import jwt
from auth_api.utils.cache import cache
from auth_api.utils.logging import setup_logging
from auth_api.utils.user_context import _get_context

setup_logging(os.path.join(_Config.PROJECT_ROOT, "logging.conf"))


def create_app(run_mode=os.getenv("DEPLOYMENT_ENV", "production")):
    """Return a configured Flask App using the Factory method."""
    app = Flask(__name__)
    app.config["ENV"] = run_mode
    app.config.from_object(config.CONFIGURATION[run_mode])

    CORS(app, resources="*")
    db.init_app(app)

    if run_mode == "migration":
        Migrate(app, db)
        app.logger.info("Running migration upgrade.")
        with app.app_context():
            execute_migrations(app)
        # Alembic has it's own logging config, we'll need to restore our logging here.
        setup_logging(os.path.join(_Config.PROJECT_ROOT, "logging.conf"))
        app.logger.info("Finished migration upgrade.")
        app.logger.info("Note: endpoints will 404 until the DEPLOYMENT_ENV is switched off of migration.")
    else:
        flags.init_app(app)
        ma.init_app(app)
        queue.init_app(app)
        mail.init_app(app)
        endpoints.init_app(app)

        app.after_request(convert_to_camel)

        ExceptionHandler(app)
        setup_403_logging(app)
        setup_jwt_manager(app, jwt)
        register_shellcontext(app)
        build_cache(app)

    return app


def setup_403_logging(app):
    """Log setup for forbidden."""
    if app.config.get("ENABLE_403_LOGGING") is True:

        @app.errorhandler(403)
        def handle_403_error(error):
            user_context = _get_context()

            user_name = user_context.user_name[:5] + "..."
            roles = user_context.roles
            app.logger.error(f"403 Forbidden - {request.method} {request.url} - {user_name} - {roles}")

            message = {"message": getattr(error, "message", error.description)}
            headers = {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"}
            return message, error.code, headers


def execute_migrations(app):
    """Execute the database migrations."""
    try:
        upgrade(directory="migrations", revision="head", sql=False, tag=None)
    except Exception as e:  # NOQA pylint: disable=broad-except
        app.logger.disabled = False
        error_message = f"Error processing migrations: {e}\n{traceback.format_exc()}"
        app.logger.error(error_message)
        raise e


def setup_jwt_manager(app, jwt_manager):
    """Use flask app to configure the JWTManager to work for a particular Realm."""

    def get_roles(a_dict):
        return a_dict["realm_access"]["roles"]  # pragma: no cover

    app.config["JWT_ROLE_CALLBACK"] = get_roles

    jwt_manager.init_app(app)


def register_shellcontext(app):
    """Register shell context objects."""
    from auth_api import models  # pylint: disable=import-outside-toplevel

    def shell_context():
        """Shell context objects."""
        return {"app": app, "jwt": jwt, "db": db, "models": models}  # pragma: no cover

    app.shell_context_processor(shell_context)


def build_cache(app):
    """Build cache."""
    cache.init_app(app)
    with app.app_context():
        cache.clear()
        if not app.config.get("TESTING", False):
            try:
                # pylint: disable=import-outside-toplevel
                from auth_api.services.permissions import Permissions as PermissionService
                from auth_api.services.products import Product as ProductService

                PermissionService.build_all_permission_cache()
                ProductService.build_all_products_cache()
            except Exception as e:  # NOQA # pylint:disable=broad-except
                error_msg = f"Error on caching {e}"
                app.logger.error(error_msg)
