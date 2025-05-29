# utils/logger.py - Para usar en todos los microservicios
import logging
import sys
from flask import request
import json


def setup_logger(name, level=logging.INFO):
    """
    Configurar logger para microservicios
    """
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger


def log_request(logger):
    """
    Decorator para logear requests HTTP
    """

    def decorator(f):
        def wrapper(*args, **kwargs):
            logger.info(f"Request: {request.method} {request.path} - IP: {request.remote_addr}")
            response = f(*args, **kwargs)
            logger.info(f"Response: {response[1] if isinstance(response, tuple) else 200}")
            return response

        wrapper.__name__ = f.__name__
        return wrapper

    return decorator