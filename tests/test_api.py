import akshare as ak

stock_sh_a_spot_em = ak.stock_sh_a_spot_em()
print(stock_sh_a_spot_em)
stock_sh_a_spot_em.to_csv("stock_sh_a_spot_em.csv", index=False)