import json
import logging
import sys

# import google.cloud.logging
# from google.cloud.logging.handlers import CloudLoggingHandler

import datetime
import os
import platform

import config


def get_stream_handler(level=logging.INFO):
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(logging.Formatter(config.LOGGING_FORMAT, datefmt=config.LOGGING_DATEFORMAT))
    return stream_handler


# def get_google_handler(level=logging.INFO):
#     os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "config/service-account.json"
#     client = google.cloud.logging.Client(project="cdz-bot-solver")
#     # client.setup_logging()
#     google_handler = CloudLoggingHandler(client)
#     google_handler.setLevel(level)
#     google_handler.setFormatter(logging.Formatter(config.LOGGING_FORMAT, datefmt=config.LOGGING_DATEFORMAT))
#     return google_handler


def get_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(level)

    logger.handlers = []
    logger.addHandler(get_stream_handler(level=level))
    return logger


# def parse_list_locals(loc: list):
#     ret = []
#     for t in loc:
#         if isinstance(t, (str, int, float, bool)) or t is None:
#             ret.append(t)
#     return ret


# def parse_function_locals(loc: dict) -> dict:
#     ret = {}
#     for key, value in loc.items():
#         if isinstance(key, str) and key.startswith("_"):
#             continue
#
#         if isinstance(value, (str, int, float, bool)) or value is None:
#             ret[key] = value
#
#         else:
#             r = {}
#             val = value
#             if not isinstance(val, dict):
#                 if "json" in dir(val):
#                     try:
#                         val = val.json()
#                         if isinstance(val, str):
#                             val = json.loads(val)
#                     except pydantic_core._pydantic_core.PydanticSerializationError:
#                         return {}
#                 else:
#                     try:
#                         val = vars(val)
#                     except TypeError:
#                         return {}
#
#             for k, v in val.items():
#                 if isinstance(k, str) and k.startswith("_"):
#                     continue
#                 if isinstance(v, (str, int, float, bool)) or v is None:
#                     r[k] = v
#                 if isinstance(v, list):
#                     r[k] = parse_list_locals(v)
#                 if isinstance(v, dict):
#                     r[k] = parse_function_locals(v)
#             ret[key] = r
#     return ret
#
#
# def get_extra_by_locals(loc):
#     return {"json_fields": {"data": parse_function_locals(loc)}}


if __name__ == "__main__":
    logger = get_logger("test")
    # logger.info("TEST", extra={"json_fields": parse_function_locals(locals())})
