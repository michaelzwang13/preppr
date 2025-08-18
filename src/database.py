import pymysql.cursors
from flask import g, current_app
from .logging_config import get_logger

logger = get_logger("preppr.database")


def get_db():
    """
    Connects to the specific database.
    """
    if "db" not in g:
        try:
            g.db = pymysql.connect(
                host=current_app.config["DB_HOST"],
                port=current_app.config["DB_PORT"],
                user=current_app.config["DB_USER"],
                password=current_app.config["DB_PASSWORD"],
                db=current_app.config["DB_NAME"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            logger.debug(
                "Database connection established",
                extra={
                    "host": current_app.config["DB_HOST"],
                    "port": current_app.config["DB_PORT"],
                    "database": current_app.config["DB_NAME"],
                },
            )
        except Exception as e:
            logger.error(
                "Failed to connect to database",
                extra={
                    "host": current_app.config["DB_HOST"],
                    "port": current_app.config["DB_PORT"],
                    "database": current_app.config["DB_NAME"],
                    "error": str(e),
                },
                exc_info=True,
            )
            raise
    return g.db


def close_db(e=None):
    """
    Closes the database again at the end of the request.
    """
    db = g.pop("db", None)
    if db is not None:
        try:
            db.close()
            logger.debug("Database connection closed")
        except Exception as ex:
            logger.error(
                "Error closing database connection",
                extra={"error": str(ex)},
                exc_info=True,
            )


def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
