import subprocess
import time
import requests
from dotenv import load_dotenv
import os
import logging

load_dotenv()

# -------- CONFIG --------
WAHA_API_KEY = os.getenv("WAHA_API_KEY")
WAHA_BASE_URL = os.getenv("WAHA_BASE_URL")
OLLAMA_URL = os.getenv("OLLAMA_URL")
SESSION_NAME = os.getenv("SESSION_NAME")
VENV_PYTHON = os.path.join("venv", "bin", "python")

# -------- LOGGER --------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


# -------- UTILS --------
def timed(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = round(time.time() - start, 2)
        logger.info(f"{func.__name__} completed in {duration}s")
        return result

    return wrapper


# -------- FUNCTIONS --------


@timed
def run_docker():
    logger.info("Starting Docker containers...")
    subprocess.run(["docker", "compose", "up", "-d"])


def start_ollama():
    logger.info("Starting Ollama...")

    try:
        subprocess.Popen(
            ["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(2)
        logger.info("Ollama start command issued")
    except Exception:
        logger.exception("Error starting Ollama")


def wait_for_ollama():
    logger.info("Checking Ollama...")

    url = f"{OLLAMA_URL}/api/tags"

    while True:
        try:
            res = requests.get(url, timeout=2)
            if res.status_code == 200:
                logger.info("Ollama is running ✅")
                return
        except Exception:
            logger.debug("Ollama not ready yet")

        logger.info("Waiting for Ollama...")
        time.sleep(2)


@timed
def load_model():
    logger.info("Warming up model...")

    url = f"{OLLAMA_URL}/api/generate"

    payload = {"model": "mistral", "prompt": "hi", "stream": False}

    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            logger.info("Model warmed up ✅")
        else:
            logger.error(f"Model warmup failed: {res.text}")
    except Exception:
        logger.exception("Error warming model")


def wait_for_waha():
    logger.info("Waiting for WAHA API...")

    url = f"{WAHA_BASE_URL}/api/sessions"
    headers = {"x-api-key": WAHA_API_KEY}

    while True:
        try:
            res = requests.get(url, headers=headers, timeout=2)
            if res.status_code == 200:
                logger.info("WAHA API is ready ✅")
                return
        except Exception:
            logger.debug("WAHA not ready yet")

        logger.info("Retrying WAHA...")
        time.sleep(2)


def wait_for_session_ready():
    logger.info("Waiting for WhatsApp session...")

    url = f"{WAHA_BASE_URL}/api/sessions"
    headers = {"x-api-key": WAHA_API_KEY}

    while True:
        try:
            res = requests.get(url, headers=headers, timeout=2)

            if res.status_code == 200:
                sessions = res.json()

                for s in sessions:
                    if s.get("name") == SESSION_NAME:
                        status = s.get("status")

                        logger.info(f"Session status: {status}")

                        if status == "WORKING":
                            logger.info("Session is ready ✅")
                            return

        except Exception:
            logger.exception("Error checking session")

        time.sleep(2)


@timed
def start_session():
    logger.info("Starting session...")

    url = f"{WAHA_BASE_URL}/api/sessions/start"
    headers = {"Content-Type": "application/json", "x-api-key": WAHA_API_KEY}

    payload = {"name": SESSION_NAME}

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        logger.info(f"Session start response: {res.status_code}")
        logger.debug(f"Session response body: {res.text}")
    except Exception:
        logger.exception("Failed to start session")


def run_server():
    logger.info("Starting Flask server...")

    subprocess.run([VENV_PYTHON, "server.py"])


# -------- MAIN --------


def main():
    logger.info("===== STARTING JARVIS SYSTEM =====")

    start_ollama()

    run_docker()
    wait_for_waha()

    wait_for_ollama()

    start_session()
    wait_for_session_ready()

    load_model()

    logger.info("===== SYSTEM READY 🚀 =====")

    run_server()


if __name__ == "__main__":
    main()
