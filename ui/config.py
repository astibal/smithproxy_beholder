import copy
import json
import logging
import os
import threading
import ssl

class Config:
    lock = threading.RLock()
    _default_app_dir = "SxWhApp"

    default_config = {
        'project_path': os.path.join(os.path.expanduser('~'), _default_app_dir),
        'address': '127.0.0.1',
        'port': 5000,
        'api_key': "123",
        'use_tls': False,
        'cert_path': os.path.join(os.path.expanduser('~'), _default_app_dir, 'cert.pem'),
        'key_path': os.path.join(os.path.expanduser('~'), _default_app_dir, 'key.pem'),
        'ca_file': os.path.join(os.path.expanduser('~'), _default_app_dir, '')
    }
    config = {}
    config_path = os.path.join(os.path.expanduser('~'), '.smithproxy')
    config_file = config_path + '/sxwhapp.json'

    ssl_context = None

    @staticmethod
    def load_config():
        try:
            with Config.lock:
                if not os.path.exists(Config.config_path):
                    os.makedirs(Config.config_path, exist_ok=True)

                if not os.path.exists(Config.config_file):
                    with open(Config.config_file, 'w') as f:
                        json.dump(Config.default_config, f)

                with open(Config.config_file, 'r') as f:
                    _def = copy.deepcopy(Config.default_config)
                    _def.update(json.load(f))
                    Config.config = _def

                keyfile = Config.config['key_path']
                certfile = Config.config['cert_path']

                if Config.config['use_tls'] and  keyfile and certfile:
                    try:
                        cx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                        cx.load_cert_chain(keyfile=keyfile, certfile=certfile)
                        Config.ssl_context = cx
                    except Exception as e:
                        logging.error(f"error creating TLS context: {e}")

                if Config.config['ca_file']:
                    from ui.remotes import options
                    options.ca_bundle = Config.config['ca_file']
                    logging.info(f"remotes ca bundle set {options.ca_bundle}")

        except FileNotFoundError as e:
            logging.fatal(f"Config.load_config: {e}")

    @staticmethod
    def save_config():
        try:
            with Config.lock:
                if not os.path.exists(Config.config_path):
                    os.makedirs(Config.config_path, exist_ok=True)

                with open(Config.config_file, 'w') as f:
                    json.dump(Config.config, f, indent=4)
        except FileNotFoundError as e:
            logging.fatal(f"Config.load_config: {e}")

    @staticmethod
    def save_content_script(slot_number: int, content: str):
        with Config.lock:
            cnfp = Config.config['project_path']

        if not os.path.exists(cnfp):
            os.makedirs(cnfp, exist_ok=True)

        with open(os.path.join(cnfp, f'slot_{slot_number}.py'), 'w') as f:
            f.write(content)

    @staticmethod
    def load_content_script(slot_number: int) -> str:
        with Config.lock:
            cnfp = Config.config['project_path']

        try:
            if not os.path.exists(cnfp):
                os.makedirs(cnfp, exist_ok=True)

            with open(os.path.join(cnfp, f'slot_{slot_number}.py'), 'r') as f:
                return f.read()

        except FileNotFoundError as e:
            logging.error(f"Config.load_config: {e}")
