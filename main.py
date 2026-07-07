#!/usr/bin/env python3
"""PDF Translator — English to literary Bengali CLI agent."""

import os
import logging

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler("logs/translation.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

from src.cli_agent import AgentCLI

AgentCLI().run()
