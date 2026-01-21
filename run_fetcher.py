import subprocess
import time
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Watcher] - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FetcherWatcher")

def run_fetcher():
    """Run the fetcher engine in a subprocess and restart it if it crashes"""
    fetcher_module = "app.services.fetcher_engine"
    
    while True:
        logger.info(f"Starting fetcher process: python -m {fetcher_module}")
        
        try:
            # Use sys.executable to ensure we use the same python interpreter
            process = subprocess.Popen(
                [sys.executable, "-m", fetcher_module],
                cwd=str(Path(__file__).parent)
            )
            
            # Wait for the process to complete
            process.wait()
            
            exit_code = process.returncode
            logger.warning(f"Fetcher process exited with code {exit_code}")
            
            # If exited normally (0), maybe we shouldn't restart immediately if it was intentional?
            # But FetcherEngine.run_forever should run forever.
            
        except KeyboardInterrupt:
            logger.info("Watcher stopping...")
            if 'process' in locals() and process.poll() is None:
                process.terminate()
            break
        except Exception as e:
            logger.error(f"Error running fetcher process: {e}")
            
        logger.info("Restarting fetcher in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    run_fetcher()
