import akshare as ak
import pandas as pd
import pandas_ta as ta
from datetime import datetime

def get_tail_strategy_v3():
    print(f"执行版本V3... 当前时间: {datetime.now().strftime('%H:%M:%S')}")
    
    # 1. 实时行情快照
    df_spot = ak.stock_zh_a_spot_em()
    for col in ['涨跌幅', '换手率', '最新价', '成交额']:
        df_spot[col] = pd.to_numeric(df_spot[col], errors='coerce')
    
    # 初筛逻辑
    mask = (
        (df_spot['涨跌幅'] >= 2.0) & (df_spot['涨跌幅'] <= 9.5) & 
        (df_spot['换手率'] >= 2.0) & 
        (~df_spot['名称'].str.contains("ST|N|C")) &
        (df_spot['代码'].str.startswith(('60', '00', '30')))
    )
    filtered_df = df_spot[mask].copy()
    
    # 关键优化：按成交额排序，只取前50只活跃度最高的进行技术面分析
    filtered_df = filtered_df.sort_values(by="成交额", ascending=False).head(50)
    print(f"初筛完成，正在深度分析前 {len(filtered_df)} 只高成交额个股...")

    final_list = []
    
    for _, item in filtered_df.iterrows():
        code = item['代码']
        try:
            # 2. 获取日线 (计算RSI)
            df_hist = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(35)
            df_hist = df_hist.rename(columns={'收盘': 'close', '开盘': 'open', '最高': 'high', '最低': 'low'})
            df_hist.ta.rsi(length=14, append=True)
            current_rsi = df_hist['RSI_14'].iloc[-1]
            
            # 3. 获取分时 (计算均价)
            df_min = ak.stock_zh_a_hist_min_em(symbol=code, period='1', adjust="qfq")
            # 统一列名以防止 KeyError
            df_min.columns = ['时间', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '最新价']
            
            # 自动识别最新的交易日期
            last_date = df_min['时间'].str.split(' ').str[0].iloc[-1]
            df_today = df_min[df_min['时间'].str.contains(last_date)].copy()
            
            # A股均价 = 累计成交额 / 累计成交量
            # 如果接口返回的成交额是元，成交量是股，则结果正确
            avg_price = df_today['成交额'].sum() / df_today['成交量'].sum()
            current_price = item['最新价']
            
            # 判定条件：股价 > 均价 且 RSI 处于 45-75 强势区间
            if current_price > avg_price and 45 < current_rsi < 75:
                final_list.append({
                    "代码": code,
                    "名称": item['名称'],
                    "当前价": current_price,
                    "均价": round(avg_price, 2),
                    "偏离度%": round(((current_price-avg_price)/avg_price)*100, 2),
                    "RSI": round(current_rsi, 2),
                    "涨幅%": item['涨跌幅']
                })
        except Exception as e:
            # print(f"{code} 分析失败: {e}")
            continue

    return pd.DataFrame(final_list)

results = get_tail_strategy_v3()
if not results.empty:
    print("\n✅ 符合条件的尾盘强势股（按偏离度升序）：")
    print(results.sort_values(by="偏离度%").to_string(index=False))
else:
    print("\n❌ 深度筛选后无符合条件的个股。")