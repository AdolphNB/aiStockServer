我要在服务器中搭建了一个 server，定时会去获取一些股票异动和资金流动信息。这个 server 的代码是一个独立的工程放在 remoteServer 文件夹中。

这个 server 运行在 ubuntu 服务器上，然后通过http://www.mcptools.xin访问。
这个 server 提供以下功能：

1. 运行 server 后，一个进程（或线程）会定时的获取股票异动、获取资金流动等信息，主要是在交易日的 9:30-11:30 和 13:00-15:00 之间获取信息。其它时间不获取信息。获取的这些信息存储在内存中，client 请求数据时，再具体从内存中读取信息分发给请求的 client.
2. 提供一个接口可以让 client 订阅这些信息。当前项目的配置选项卡下，可以提供订阅按键（点订阅会弹窗，出现微信二维码付款。）付款（有 1 月、3 月、6 月、12 月）完成后，将订阅信息保存到数据库中，也会生成一个 token, 这个 token 用来标识订阅信息给到 PC client。
3. 这个 server 提供一个接口，PC client 可以通过这个接口获取订阅信息。可供 20 个用户同时访问，因此要考虑负载均衡。
4. 我还需要建立一个后台管理界面，可以管理订阅信息，包括查看订阅信息、修改订阅信息、删除订阅信息等。可以通过www.mcptools.xin/admin访问。

定时获取股票异动和资金流动信息，暂时只提供一个接口， 但是这个要是一个获立的文件，方便我日后扩展其它接口：
赚钱效应分析
import akshare as ak
stock_market_activity_legu_df = ak.stock_market_activity_legu()
print(stock_market_activity_legu_df)