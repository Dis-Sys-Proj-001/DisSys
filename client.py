import socket
from serialization_old import deserialize, serialize, Message, unmarshalling, marshalling
# from serialization import deserialize, serialize, Message, unmarshalling, marshalling
#############新写的那部分哈希有些问题，会报错#################3



def send_message(socket1, server_addr, request_msg, identifier):
    msg_list = marshalling(request_msg, identifier)
    for item in msg_list:
        # print(len(item))
        socket1.sendto(item, server_addr)



def receive_message(socket1:socket, server_addr, timeout = 5.0):
    resend_flag = 1 # 重发标志位，若最终为1则接收出错，若最终为0则要求重发
    
    while resend_flag == 1:
        socket1.settimeout(timeout)    # 设置超时设置
        try:
            msg_byte, Saddr = socket1.recvfrom(512)
            msg_byte_list = [msg_byte]
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
        # 要求客户端重发信息
        if resend_flag == 1:
            send_message(socket1, server_addr, "Error: Please resent the request!", 999)
    # 成功接收到完整消息
    original_text, the_identifier = unmarshalling(msg_byte_list)
    return original_text, the_identifier






def get_parameters(num_params):
    parameters = []
    for i in range(num_params):
        param = input(f"请输入参数 {i+1}: ")
        parameters.append(param)
    return parameters



def start_Client(server_addr, freshness_interval, semantics):
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    identifier = 0
    options = {
        "1": {"display_name": "Read", "function_name": "read_file", "params": 3},
        "2": {"display_name": "Insert", "function_name": "insert_content", "params": 3},
        "3": {"display_name": "Monitor updates", "function_name": "monitor_updates", "params": 2},
        "4": {"display_name": "View file list", "function_name": "file_list", "params": 1},
        "5": {"display_name": "Rename file", "function_name": "rename_file", "params": 2},
        "6": {"display_name": "Manual Input", "function_name": "", "params": 4},
        "7": {"display_name": "Exit", "function_name": "Exit", "params": 0}
    }

    while True:
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
            if choice == "6": 
                print(parameters)
                request_msg = f"{','.join(parameters)}"
            else:
                request_msg = f"{options[choice]['function_name']},{','.join(parameters)}"
            print("发送的命令：", request_msg)
            # 发送请求
            # request_msg = "---------Requset----------"
            identifier = (identifier + 1) %256
            success = 0
            while success != 1:
                send_message(c, server_addr, request_msg, identifier)
                print("发送完毕!")

                # 接收响应
                response_text, _ = receive_message(c, server_addr, 5)   
                # print("Received response:", response_text)
                if response_text == "Error: Please resent the request!":
                    print("请求丢失错误，重发中......")
                else: 
                    success = 1
                    print("Received response:", response_text)
                    # 进行收到后的操作

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



