# Stock Data Directory

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
