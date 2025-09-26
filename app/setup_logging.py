import logging, sys

def setup_logging(level: str = "INFO"):
    logger = logging.getLogger()
    if logger.handlers:  # don’t double add during reload
        return
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    h = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s :: %(message)s"
    )
    h.setFormatter(fmt)
    logger.addHandler(h)
