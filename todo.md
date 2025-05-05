## 当前log
anp_llmagent开发：一条命令创建并启动agent-did
    需要设计agent-pool
anp_llmapp开发：一条命令连接agent的过程
    需要设计llmapp的agent-bookmark


## 计划工作

anp_llmagent 搭建
    支持anp双向验证did 建立加密通道
    支持mcp接口调用本地功能对外anp服务
    支持动态开放多个anp能力接口
    支持对接flow事件和MultiAgent框架，将anp通信传入传出
mcp接口服务的web hosting
anp自身份与其他用户身份管理发布
未来示例以 anp_llmapp/mcp 与 anp_llmagent互联为主要场景
通讯加密问题——post/get和websocket下如何加密，能否不依赖域名和https

## 问题与bug

1. 当前版本
    Trae sse mcp 连接消息发送失败
    mcp dev stdio 消息发送失败
    stdio 客户端测试比较正常 也会偶发服务器问题
    猜想问题出在resp的服务启动上概率大