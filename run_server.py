import os
import signal
import subprocess
import sys
import time
import logging
import shutil
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Orchestrator")

# Constants
SHARED_CACHE_DIR = "shared_cache"
API_PROCESS = None
FETCHER_PROCESS = None

def cleanup():
    """Cleanup processes and cache files"""
    global API_PROCESS, FETCHER_PROCESS
    
    logger.info("Cleaning up...")
    
    # Terminate processes
    if FETCHER_PROCESS:
        logger.info("Terminating Fetcher Engine...")
        FETCHER_PROCESS.terminate()
        
    if API_PROCESS:
        logger.info("Terminating API Server...")
        API_PROCESS.terminate()
        
    # Wait for processes to exit
    if FETCHER_PROCESS:
        FETCHER_PROCESS.wait()
    if API_PROCESS:
        API_PROCESS.wait()
        
    # Clean up shared cache
    if os.path.exists(SHARED_CACHE_DIR):
        logger.info(f"Removing shared cache directory: {SHARED_CACHE_DIR}")
        try:
            # We only remove .csv and .tmp files as per requirement
            for root, dirs, files in os.walk(SHARED_CACHE_DIR):
                for file in files:
                    if file.endswith(('.csv', '.tmp')):
                        os.remove(os.path.join(root, file))
            logger.info("Shared cache cleaned.")
        except Exception as e:
            logger.error(f"Error cleaning cache: {e}")

def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}, exiting...")
    cleanup()
    sys.exit(0)

def start_fetcher():
    """Start the Fetcher Engine process"""
    global FETCHER_PROCESS
    logger.info("Starting Fetcher Engine...")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    FETCHER_PROCESS = subprocess.Popen([sys.executable, "-m", "app.services.fetcher_engine"], env=env)

def start_api():
    """Start the API Server (FastAPI) process"""
    global API_PROCESS
    logger.info("Starting API Server...")
    # Use uvicorn to start the app
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    API_PROCESS = subprocess.Popen([sys.executable, "-m", "app.main"], env=env)

def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ensure cache directory exists
    os.makedirs(SHARED_CACHE_DIR, exist_ok=True)
    
    try:
        # Start processes
        start_fetcher()
        # Give fetcher some time to start and create initial files if needed
        time.sleep(2)
        start_api()
        
        logger.info("System is up and running. Press Ctrl+C to stop.")
        
        # Monitor processes
        while True:
            if FETCHER_PROCESS.poll() is not None:
                logger.error("Fetcher Engine process died! Restarting...")
                start_fetcher()
            
            if API_PROCESS.poll() is not None:
                logger.error("API Server process died! Restarting...")
                start_api()
                
            time.sleep(5)
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()
