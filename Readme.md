### 12:50 同步版本
 - UDPServer：凌晨群里版本
 - serialization: 凌晨群里版本
 - client.py：12:50版本，比凌晨群里更新
 - server.py：一个随便写的测试client.py的程序
 - serialization_old: 不带哈希校验的版本
 - client.py serialization_old server.py 这仨能组合在一起跑起来

### Todo:

#### client
 - 执行结果的回显
 - 两种语义
 - caching 
 - 本地文件监视，一旦发生改变就

#### server
 - caching 应该是id+address

#### others
 - server client对接和调试，
 - 重发的测试（这个弄不好也没关系）