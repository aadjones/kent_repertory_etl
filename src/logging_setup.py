import logging
import logging.config
import os

import yaml


def setup_logging(
    default_path: str = "logging_config.yaml", default_level: int = logging.DEBUG, env_key: str = "LOG_CFG"
):
    """
    Setup logging configuration.

    Tries to load logging configuration from a YAML file.
    The path to the config file can be overridden by setting an environment variable (env_key).
    If the file doesn't exist or an error occurs, it falls back to basic logging configuration.

    Parameters:
      - default_path: the default path to the logging config YAML file.
      - default_level: the default logging level if no config file is found.
      - env_key: the environment variable that can override the default path.
    """
    path = os.getenv(env_key, default_path)
    if os.path.exists(path):
        try:
            with open(path, "rt") as f:
                config = yaml.safe_load(f.read())
            logging.config.dictConfig(config)
            logging.getLogger(__name__).debug(f"Loaded logging configuration from {path}")
        except Exception as e:
            print(f"Error in logging configuration file: {e}. Using basic config.")
            logging.basicConfig(level=default_level)
    else:
        logging.basicConfig(level=default_level)
        logging.getLogger(__name__).debug("No logging configuration file found. Using basic configuration.")


# If you want the logging configuration to be set up immediately upon importing this module,
# you can call setup_logging() here. Otherwise, call it explicitly from your main entry point.
if __name__ == "__main__":
    setup_logging()
    # Example logging to test the configuration
    logger = logging.getLogger(__name__)
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")
