"""
Logging configurado
"""

import logging
import sys


def setup_logger():
    """Configura logger principal"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger("bomtempo")


def get_logger(name):
    """Retorna logger específico"""
    return logging.getLogger(f"bomtempo.{name}")
