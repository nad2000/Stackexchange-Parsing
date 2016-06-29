import configparser
import sys
import os

try:
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
    __config = configparser.ConfigParser()
    __config.read(config_file)
    __config = {k:v for s in __config.sections() for k,v in __config[s].items()}
except:
    print("Missing or malformated configuration file %r." % config_file)
    sys.exit(-1)

OUTPUT_DIR = __config.get("output_dir", "stackexchange_jsons")
LOG_DIR = __config.get("log_dir", "stackexchange_issues")

# Stackoverflow API:
API_BASE = __config.get("api_base", "https://api.stackexchange.com/")
API_VERSION = __config.get("api_version", "2.2")
API_BASE_URL = API_BASE + API_VERSION + '/'

# S3:
S3_ACCESS_KEY = __config.get("access_key")
S3_SECRET_KEY = __config.get("secret_key")
S3_BUCKET = __config.get("bucket")
