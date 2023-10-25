import socket
import time
from serialization_old import deserialize, serialize, Message, unmarshalling, marshalling
# from serialization import deserialize, serialize, Message, unmarshalling, marshalling
#############新写的那部分哈希有些问题，会报错#################3

options = {
    "1": {"display_name": "Read", "function_name": "read_file", "params": 3},
    "2": {"display_name": "Insert", "function_name": "insert_content", "params": 3},
    "3": {"display_name": "Monitor updates", "function_name": "monitor_updates", "params": 2},
    "4": {"display_name": "View file list", "function_name": "file_list", "params": 1},
    "5": {"display_name": "Rename file", "function_name": "rename_file", "params": 2},
    "6": {"display_name": "Manual Input", "function_name": "", "params": 4},
    "7": {"display_name": "Exit", "function_name": "Exit", "params": 0}
}

def send_message(socket1, server_addr, request_msg, identifier):
    msg_list = marshalling(request_msg, identifier)
    for item in msg_list:
        socket1.sendto(item, server_addr)



def receive_message(socket1:socket, server_addr, timeout = 100):
    resend_flag = 1 # 重发标志位，若最终为1则接收出错，若最终为0则要求重发
    resend_times = 0
    while resend_flag == 1 and resend_times < 10:
        socket1.settimeout(timeout)    # 设置超时设置
        try:
            msg_byte, Saddr = socket1.recvfrom(512)
            msg_byte_list = [msg_byte, ]
            msg_object_temp = deserialize(msg_byte_list[0])


            block_num = msg_object_temp.total_blocks
            if msg_object_temp.block_index != 0:  # 第一次收到的块不是第一块，肯定出问题了，大概是丢失消息
                pass    # 有问题，到后面请求重发吧
            elif block_num == 1:    # 这是一个单块的请求
                resend_flag = 0 # 成功接收信息
            elif block_num != 1:  # 这是一个多块的请求，这是收到的第一块    
                # msg = str(deserialize(msg_list[0]).data)
                # 设置超时时间，单位为秒
                socket1.settimeout(timeout)
                for i in range(1, block_num):
                    # 逐次接收后面的块
                    msg_byte, Saddr1 = socket1.recvfrom(512)
                    msg_byte_list.append(msg_byte)
                    msg_object_temp = deserialize(msg_byte_list[-1])
                    if msg_object_temp.block_index == i:    # 接收到新块，这块的顺序是对的
                        if block_num == msg_object_temp.block_index: # 这是不是分块消息的最后一块
                            resend_flag = 0 # 最后一块也成功接收了，整条请求接收完毕
                    else:   # 接收到的顺序是乱的
                        resend_flag = 1
                        break 
                    
            else: # 第一次收到的块不是第一块，肯定出问题了
                resend_flag = 1
        except socket.timeout:  # 不管是哪一次需要接收消息时超时，就会激活重发
            print("Receive operation timed out")
            resend_flag = 1
        # 成功接收到完整消息
        original_text, the_identifier = unmarshalling(msg_byte_list)
        if original_text == False:  # 但是hash验证失败
            resend_flag = 1

        # 要求客户端重发信息
        if resend_flag == 1:
            resend_times = resend_times + 1
            send_message(socket1, server_addr, "Error: Please resent the request!", 999)
    # 接收到的信息完整且正确
    socket1.setblocking(0)
    return original_text, the_identifier



def echo_response(msg_list, response_text):
    # function_name = options[msg_list[0]]['function_name']
    function_name = msg_list[0]
    if function_name == 'read_file':
        content = response_text
        print("读取成功！文件内容如下：")
        # print(content.decode('utf-8'))
        print(content)




    elif function_name == 'insert_content':
        if response_text == "Succeed!":
            print("插入成功")
        else:
            print("插入失败：", response_text)

    elif function_name == 'monitor_updates':
        pass    # 写在主循环里了


    elif function_name == 'file_list':
        if response_text == "Path not found!":
            print("获取失败：", response_text)
        else:
            print("文件列表如下：")
            print(response_text)

    elif function_name == 'rename_file':
        if response_text == "Rename successful":
            print("Rename successful!")
        else:
            print("重命名失败：", response_text)
            

    else:
        print("未知的操作名：", function_name)
        print("响应内容：", response_text)


def get_parameters(num_params):
    parameters = []
    for i in range(num_params):
        param = input(f"请输入参数 {i+1}: ")
        parameters.append(param)
    return parameters

def start_Client(server_addr, freshness_interval, semantics):
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    identifier = 0
    read_buffer = {}


    while True:
        print("==============功能列表=================")
        for k, v in options.items():
            print(f"{k}. {v['display_name']}")
        choice = input("请选择要使用的功能，输入序号(1-7): ")

        if choice == "7":
            print("成功退出程序！")
            break

        if choice in options:
            print(f"执行功能：{options[choice]['display_name']}")
            num_params = options[choice]['params']
            parameters = get_parameters(num_params)
            # 对于特殊功能的判断
            if choice == "1":   
                # read, 使用cache
                response = read_buffer.get(tuple(parameters))
                # 如果缓存中没有找到
                if response == None:
                    pass    # 正常请求
                else:
                    msg_list = [options[choice]['function_name']]+ parameters
                    # request_msg = f"{','.join(msg_list)}"
                    print("***命中chahe!")
                    echo_response(msg_list, response)
                    continue
            
            # 生成发送的消息
            if choice == "6":   # 手动输入命令，分割其参数，提取命令名
                msg_list = parameters
            else:
                print(parameters)
                # msg_list = [options[choice]['function_name'], parameters]
                # msg_list = parameters.insert(0, str(options[choice]['function_name']))
                msg_list = [options[choice]['function_name']]+ parameters
            print(msg_list)
            request_msg = f"{','.join(msg_list)}"
            print("发送的命令：", request_msg)

            # 发送请求
            identifier = (identifier + 1) %256
            success = 0
            while success != 1:
                send_message(c, server_addr, request_msg, identifier)
                print("发送完毕!")

                # 接收响应
                response_text, _ = receive_message(c, server_addr, 100)   
                # 接收失败，重发
                if response_text == "Error: Please resent the request!":
                    print("请求丢失错误，重发中......")
                # 接收成功
                else: 
                    success = 1
                    print("Received response:", response_text)
                    # 进行收到后的操作
                    if choice != "3":
                        echo_response(msg_list ,response_text)                  
                        if choice == "1":  # 读到新东西了，更新cache一下
                            read_buffer[tuple(parameters)] = response_text
                            print("cache:\n", read_buffer)

                    elif choice == "3":  # 监听更新
                        # if response_text == "Succeed!":
                        if 1==1:
                            print("开始监听，监听", msg_list[2], "秒")
                            # 设置socket为非阻塞模式
                            c.setblocking(0)
                            start_time = time.time()
                            while time.time() - start_time < float(msg_list[2]):
                                try:
                                    data1, Saddr = receive_message(c, server_addr, 0)
                                    print("Received data:", data1, "from", Saddr)
                                    print("Updated file: \n", data1)
                                    data1 = ""
                                except socket.error:
                                    # 没有数据到来，继续等待
                                    pass
        else:
            print("无效的选择，请重新输入!")
    return c



    





if __name__ == "__main__":
    host = '127.0.0.1'
    server_addr = (host, 25896)

    c = start_Client(server_addr, 65536, "at-most-once")



    # # 发送请求
    # request_msg = "---------Requset----------"
    # identifier = (identifier + 1) %256
    # send_message(c, server, request_msg, identifier)
    # print("Sent request!")

    # # 接收响应
    # response_text, _ = receive_message(c)   
    # print("Received response:", response_text)



