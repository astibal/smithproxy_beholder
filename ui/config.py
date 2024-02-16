import json
import logging
import os
import threading


class Config:
    lock = threading.RLock()

    default_config = {
        'project_path': os.path.join(os.path.expanduser('~'), 'SxWhApp'),
    }
    config = None
    config_path = os.path.join(os.path.expanduser('~'), '.smithproxy')
    config_file = config_path + '/sxwhapp.json'
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
                     Config.config = json.load(f)
        except FileNotFoundError as e:
            logging.fatal(f"Config.load_config: {e}")

    @staticmethod
    def save_config():
        try:
            with Config.lock:
                if not os.path.exists(Config.config_path):
                    os.makedirs(Config.config_path, exist_ok=True)

                with open(Config.config_file, 'w') as f:
                     json.dump(Config.config, f)
        except FileNotFoundError as e:
            logging.fatal(f"Config.load_config: {e}")
