"""
Initialize data directory structure
Run this script to create necessary directories for data storage
"""
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_data_directories(base_dir: str = "data"):
    """Create necessary data directories"""
    base_path = Path(base_dir)
    
    directories = [
        base_path / "stock_list",
        base_path / "kline_daily",
        base_path / "kline_realtime",
        base_path / "fund_flow",
        base_path / "stock_changes",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")
    
    # Create a README in the data directory
    readme_path = base_path / "README.md"
    readme_content = """# Stock Data Directory

This directory contains all cached stock data.

## Structure

- `stock_list/`: Stock list data (股票列表)
- `kline_daily/`: Historical daily K-line data (历史日K线数据)
- `kline_realtime/`: Today's realtime minute-level data (当日分时数据)
- `fund_flow/`: Fund flow data (资金流向数据)
- `stock_changes/`: Stock changes data (盘口异动数据)

## Data Format

All data files are in CSV format with UTF-8-SIG encoding for Excel compatibility.

## Backup Strategy

- Realtime data is saved to files after market close (15:30)
- Daily K-line data is updated when fetched
- Fund flow and stock changes data are overwritten on each fetch

## Maintenance

- Old realtime data files can be deleted periodically to save space
- Daily K-line files are kept up to date automatically
"""
    
    readme_path.write_text(readme_content, encoding='utf-8')
    logger.info(f"Created README: {readme_path}")
    
    logger.info(f"Data directory structure initialized at: {base_path.absolute()}")


if __name__ == "__main__":
    init_data_directories()
    print("\n✓ Data directories initialized successfully!")
