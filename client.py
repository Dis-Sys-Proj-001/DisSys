import random
import socket
import time
from serialization_old import deserialize, serialize, Message, unmarshalling, marshalling
# from serialization import deserialize, serialize, Message, unmarshalling, marshalling


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
    # test for packet loss
    i = random.randint(0, 10)
    if i < 11:
        msg_list = marshalling(request_msg, identifier)
        for item in msg_list:
            socket1.sendto(item, server_addr)
    else:
        print('test loss of request')


def receive_message(socket1: socket, server_addr, timeout=10):
    resend_flag = 1  # 重发标志位，若最终为1则接收出错，若最终为0则要求重发
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
                resend_flag = 0  # 成功接收信息
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
                        if block_num == msg_object_temp.block_index:  # 这是不是分块消息的最后一块
                            resend_flag = 0  # 最后一块也成功接收了，整条请求接收完毕
                    else:   # 接收到的顺序是乱的
                        resend_flag = 1
                        break

            else:  # 第一次收到的块不是第一块，肯定出问题了
                resend_flag = 1
        except socket.timeout:  # 不管是哪一次需要接收消息时超时，就会激活重发
            print("Receive operation timed out")
            resend_flag = 1
        # 成功接收到完整消息
        try:
            original_text, the_identifier = unmarshalling(msg_byte_list)
            if original_text == False or original_text == "Error: resend the request!":  # 但是hash验证失败
                resend_flag = 1
        except Exception:
            resend_flag = 1

        # 要求客户端重发信息
        if resend_flag == 1:
            resend_times = resend_times + 1
            return "Error: resend the request!", 1
            # send_message(socket1, server_addr,
            #              "Error: Please resent the request!", 999)
    # 接收到的信息完整且正确
    socket1.setblocking(0)
    return original_text, the_identifier


def echo_response(msg_list, response_text):
    # function_name = options[msg_list[0]]['function_name']
    function_name = msg_list[0]
    if function_name == 'read_file':
        content = response_text
        print("Read success! The contents of the file are as follows:")
        # print(content.decode('utf-8'))
        print(content)

    elif function_name == 'insert_content':
        if response_text == "Insertion successful":
            print("Successful insertion")
        else:
            print("Fail insertion：", response_text)

    elif function_name == 'monitor_updates':
        pass    # 写在主循环里了

    elif function_name == 'file_list':
        if response_text == "Path not found!":
            print("Failed to get", response_text)
        else:
            print("file list：")
            print(response_text)

    elif function_name == 'rename_file':
        if response_text == "Rename successful":
            print("Rename successful!")
        else:
            print("Rename unsuccessful：", response_text)

    else:
        print("unknown operation：", function_name)
        print("response：", response_text)


def get_parameters(num_params):
    parameters = []
    for i in range(num_params):
        param = input(f"parameter {i+1}: ")
        parameters.append(param)
    return parameters


def start_Client(server_addr, freshness_interval, semantics):
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    identifier = 0
    read_buffer = {}

    while True:
        print("==============function list=================")
        for k, v in options.items():
            print(f"{k}. {v['display_name']}")
        choice = input("Please select the function you want to use and enter the serial number(1-7): ")

        if choice == "7":
            print("Successfully exit！")
            break

        if choice in options:
            print(f"perform function：{options[choice]['display_name']}")
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
                    msg_list = [options[choice]['function_name']] + parameters
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
                msg_list = [options[choice]['function_name']] + parameters
            print(msg_list)
            request_msg = f"{','.join(msg_list)}"
            print("request sent：", request_msg)

            # 发送请求
            identifier = (identifier + 1) % 256
            success = 0
            while success != 1:
                send_message(c, server_addr, request_msg, identifier)
                print("Sent!")

                # 接收响应
                response_text, _ = receive_message(c, server_addr, 10)
                # 接收失败，重发
                if response_text == "Error: resend the request!":
                    print("Request lost error, retransmission......")
                # 接收成功
                else:
                    success = 1
                    # print("Received response:", response_text)
                    # Act upon receipt
                    if choice != "3":
                        echo_response(msg_list, response_text)
                        if choice == "1":  # You read something new. Update the cache
                            read_buffer[tuple(parameters)] = response_text
                            print("cache:\n", read_buffer)

                    elif choice == "3":  # Listening for updates
                        # if response_text == "Succeed!":
                        if 1 == 1:
                            print("Start listening. Listening", msg_list[2], "s")
                            # Set the socket to non-blocking mode
                            c.setblocking(0)
                            start_time = time.time()
                            while time.time() - start_time < float(msg_list[2]):
                                try:
                                    data1, Saddr = receive_message(
                                        c, server_addr, 0)
                                    print("Received data:",
                                          data1, "from", Saddr)
                                    print("Updated file: \n", data1)
                                    data1 = ""
                                except socket.error:
                                    # No data is coming. Keep waiting
                                    pass
        else:
            print("Invalid selection, please re-enter!")
    return c


if __name__ == "__main__":
    host = '127.0.0.1'
    server_addr = (host, 25896)

    c = start_Client(server_addr, 65536, "at-most-once")

