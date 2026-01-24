from fastapi import APIRouter, Query, Response, HTTPException
from app.services.data_service import DataService
import pandas as pd

router = APIRouter()

@router.get("/kline/real")
async def get_realtime_kline_json(
    code: str = Query(..., description="Stock code"),
    date: str = Query(None, description="Date in YYYY-MM-DD format, defaults to today")
):
    """
    Get realtime 1-minute K-line data in standard JSON format
    """
    df = DataService.get_realtime_kline_df(code, date)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for stock {code}")
    
    # Standard JSON orient records
    return {
        "code": code,
        "date": date or pd.Timestamp.now().strftime("%Y-%m-%d"),
        "data": df.to_dict(orient='records')
    }

@router.get("/kline/real/arrow")
async def get_realtime_kline_arrow(
    code: str = Query(..., description="Stock code"),
    date: str = Query(None, description="Date in YYYY-MM-DD")
):
    """
    Get realtime 1-minute K-line data serialized in Apache Arrow (Feather) format.
    Clients can read this directly into a DataFrame without manual conversion.
    """
    df = DataService.get_realtime_kline_df(code, date)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data found")
        
    arrow_bytes = DataService.serialize_df_arrow(df)
    
    return Response(
        content=arrow_bytes,
        media_type="application/vnd.apache.arrow.file"
    )

@router.get("/kline/real/parquet")
async def get_realtime_kline_parquet(
    code: str = Query(..., description="Stock code"),
    date: str = Query(None, description="Date in YYYY-MM-DD")
):
    """
    Get realtime 1-minute K-line data in Parquet format.
    """
    df = DataService.get_realtime_kline_df(code, date)
    if df.empty:
        raise HTTPException(status_code=404, detail="No data found")
        
    parquet_bytes = DataService.serialize_df_parquet(df)
    
    return Response(
        content=parquet_bytes,
        media_type="application/octet-stream"
    )
