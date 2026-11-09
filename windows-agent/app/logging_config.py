import logging
import sys


def setup_agent_logging(level=logging.INFO):
    log_format = "%(asctime)s | [AGENT] %(levelname)-8s | %(name)s:%(lineno)d - %(message)s"
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


logger = logging.getLogger("printx-agent")

