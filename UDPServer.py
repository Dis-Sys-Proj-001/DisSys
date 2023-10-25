import socket
import os
import time
from serialization import deserialize, serialize, Message


def read_file(pathname, offset, read_length):

    if not os.path.exists(pathname):
        return "File does not exist!"

    file_size = os.path.getsize(pathname)
    if offset > file_size:
        return "Offset exceeds file size!"

    with open(pathname, 'rb') as f:
        f.seek(offset)
        content = f.read(read_length)

    return content


def insert_content(pathname, offset, sequence):

    if not os.path.exists(pathname):
        return "File does not exist!"

    file_size = os.path.getsize(pathname)
    if offset > file_size:
        return "Offset exceeds file size!"

    with open(pathname, 'rb') as f:
        initial_content = f.read(offset)

    # 读取文件从偏移量到结束的内容
    with open(pathname, 'rb') as f:
        f.seek(offset)
        remaining_content = f.read()

    # 插入序列并重写文件
    with open(pathname, 'wb') as f:
        f.write(initial_content + sequence + remaining_content)

    return "Insertion successful"


def monitor_updates(pathname, monitor_interval, address, address_list, server_socket):
    # 存储文件的最后更新时间
    last_modified_time = 0

    # 记录监控开始的时间
    monitor_start_time = time.time()

    address_list.append(address)

    while True:
        # 如果超过了监控间隔，退出循环
        if time.time() - monitor_start_time >= monitor_interval:
            address_list.remove(address)
            break

        try:
            # 获取文件的最后更新时间
            new_modified_time = os.path.getmtime(pathname)
            if new_modified_time != last_modified_time:
                # 如果文件被更新
                last_modified_time = new_modified_time
                with open(pathname, 'rb') as f:
                    content = f.read()
                    content = serialize(
                        Message(0, len(content), 1, 1, content))
                # 向所有已注册的客户端发送更新后的文件内容
                for addresses in address_list:
                    server_socket.sendto(content, addresses)
        except FileNotFoundError:
            pass

        time.sleep(1)  # 每秒检查一次


def file_list(pathname):
    try:
        items = os.listdir(pathname)
        return items
    except FileNotFoundError:
        return "Path not found!"


def rename_file(old_path, new_name):
    try:
        directory = os.path.dirname(old_path)
        new_path = os.path.join(directory, new_name)
        os.rename(old_path, new_path)
        return "Rename successful"
    except FileNotFoundError:
        return "File does not exist!"
    except Exception as e:
        return f"An error occurred: {e}"


def start_server(semantics):
    # Create a UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('localhost', 25896))

    print('UDP Server on', '127.0.0.1', ":", 25896, "......")

    # Store processed request IDs for deduplication (only used in "at-most-once" mode)
    processed_request_ids = set()
    # Store all addresses of clients requiring monitor
    address_list = []

    buffer = []

    while True:
        # resend if flag is 1
        resend_flag = 1

        while resend_flag == 1:
            msg_block, address = server_socket.recvfrom(512)
            received_msg = deserialize(msg_block)
            print(f"Received message: {received_msg.data.decode('utf-8')}")

            if (msg_block.block_index == 0) and (msg_block.total_blocks == 1):    # 这是一个单块的请求
                msg = str(msg_block.data)
                resend_flag = 0  # 成功接收信息
            elif (msg_block.block_index == 0) and (msg_block.total_blocks != 1):  # 这是一个多块的请求，这是收到的第一块
                msg = str(msg_block.data)
                # 设置超时时间，单位为秒
                server_socket.settimeout(5.0)
                for i in range(1, msg_block.total_blocks):
                    # 逐次接收后面的块
                    try:
                        msg_block = deserialize(server_socket.recvfrom(512))
                    except socket.timeout:  # 超时
                        resend_flag = 1
                        break
                    if (msg_block.block_index == i):    # 接收到新块，且该块的顺序是对的
                        msg = msg + str(msg_block.data)
                    else:   # 接收到的顺序是乱的
                        resend_flag = 1
                        break
                resend_flag = 0  # 成功接收信息
            else:  # 第一次收到的块不是第一块，肯定出问题了
                resend_flag = 1
            # 要求客户端重发信息
            requiring_resend_block = Message(
                0, 26, 1, 1, "Error: resent the request!")
            server_socket.sendto(serialize(requiring_resend_block), address)

        # Parse request
        request_id = msg[1]
        operation = msg[0]
        args = operation.split(',')

        # In "at-most-once" mode, check request ID to avoid processing duplicate requests
        if semantics == "at-most-once" and (address, request_id) in processed_request_ids:
            print(f"Duplicate request {request_id}, resending cached reply.")
            for cached_reply in buffer:
                if cached_reply[0] == address and cached_reply[1] == request_id:
                    response = cached_reply[3]
        else:
            # Perform operation
            response = "Invalid request"
            if args[0] == "read":
                response = read_file(args[1], int(args[2]), int(args[3]))
            elif args[0] == "insert":
                response = insert_content(args[1], int(args[2]), args[3])
            elif args[0] == "monitor":
                response = "Monitoring started"
                monitor_updates(args[1], int(args[2]),
                                address, address_list, server_socket)
            elif args[0] == "list_all_files":
                response = file_list(args[1])
            elif args[0] == "rename":
                response = rename_file(args[1], args[2])

        # Record the processed request ID (only in "at-most-once" mode) and cache the reply
        if semantics == "at-most-once":
            processed_request_ids.add((address, request_id))
            buffer.append((address, processed_request_ids, serialize(
                Message(0, len(response), 1, 1, response))))

        # Send response
        print(f"Sending response: {response}")
        server_socket.sendto(
            serialize(Message(0, len(response), 1, 1, response)), address)