import akshare as ak

# stock_info_a_code_name = ak.stock_info_a_code_name()
# stock_info_a_code_name.to_csv("stock_info_a_code_name.csv", index=False)

# stock_sh_a_spot_em = ak.stock_sh_a_spot_em()
# stock_sh_a_spot_em.to_csv("stock_sh_a_spot_em.csv", index=False)


# stock_sh_a_spot_em = ak.stock_sz_a_spot_em()
# stock_sh_a_spot_em.to_csv("stock_sz_a_spot_em.csv", index=False)

# stock_sh_a_spot_em = ak.stock_bj_a_spot_em()
# stock_sh_a_spot_em.to_csv("stock_bj_a_spot_em.csv", index=False)


# stock_fund_flow_individual_df = ak.stock_fund_flow_individual(symbol="即时")
# print(stock_fund_flow_individual_df)
# stock_fund_flow_individual_df.to_csv("stock_fund_flow_individual_df.csv", index=False)

# stock_board_change_em_df = ak.stock_board_change_em()
# print(stock_board_change_em_df)
# stock_board_change_em_df.to_csv("stock_board_change_em_df.csv", index=False)

stock_hot_rank_latest_em_df = ak.stock_hot_rank_latest_em(symbol="sh600550")
print(stock_hot_rank_latest_em_df)
stock_hot_rank_latest_em_df.to_csv("stock_hot_rank_latest_em_df.csv", index=False)