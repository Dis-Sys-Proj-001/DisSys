import random
import socket
import os
import time
from serialization_old import unmarshalling, marshalling, serialize, deserialize, Message
# from serialization import unmarshalling, marshalling, serialize, deserialize, Message


def read_file(pathname, offset, read_length):

    if not os.path.exists(pathname):
        return "File does not exist!"

    file_size = os.path.getsize(pathname)
    if offset > file_size:
        return "Offset exceeds file size!"

    with open(pathname, 'rb') as f:
        f.seek(offset)
        content = f.read(read_length)

    return str(content)


def insert_content(pathname, offset, sequence):

    if not os.path.exists(pathname):
        return "File does not exist!"

    file_size = os.path.getsize(pathname)
    if offset > file_size:
        return f"Offset {offset} exceeds file size {file_size}!"

    with open(pathname, 'rb') as f:
        initial_content = f.read(offset)

    # Reads the contents of a file from the offset to the end
    with open(pathname, 'rb') as f:
        f.seek(offset)
        remaining_content = f.read()

    # Insert the sequence and overwrite the file
    with open(pathname, 'wb') as f:
        f.write(initial_content + bytes(sequence, 'utf-8') + remaining_content)

    return "Insertion successful"


def monitor_updates(pathname, monitor_interval, address, address_list, server_socket):
    # The last update time of the stored file
    last_modified_time = os.path.getmtime(pathname)

    # Record the time when the monitoring starts
    monitor_start_time = time.time()

    address_list.append(address)

    while True:
        # If the monitoring interval is exceeded, exit the loop
        if time.time() - monitor_start_time >= monitor_interval:
            address_list.remove(address)
            for expire_alert in marshalling("Monitor-interval expired", 0):
                server_socket.sendto(expire_alert, address)
            break

        try:
            # Gets the last update time of the file
            new_modified_time = os.path.getmtime(pathname)
            if new_modified_time - last_modified_time > 0.5:
                # If the file is updated
                last_modified_time = new_modified_time
                with open(pathname, 'rb') as f:
                    content = f.read()
                    contents = marshalling(str(content), 0)
                # Send the updated file content to all registered clients
                for addresses in address_list:
                    for content in contents:
                        server_socket.sendto(content, addresses)
        except FileNotFoundError:
            pass

        time.sleep(1)  # Check it every second


def file_list(pathname):
    try:
        items = os.listdir(pathname)
        return items
    except FileNotFoundError and NotADirectoryError:
        return "Path error or not found!"


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
    # Store past reply message
    buffer = []

    while True:
        resend_times = 0
        resend_flag = 1
        while resend_flag == 1 and resend_times < 10:
            try:
                server_socket.setblocking(True)
                msg_block, address = server_socket.recvfrom(
                    512)
                msg_block_list = [msg_block]
                received_msg = deserialize(msg_block_list[0])
                block_num = received_msg.total_blocks
                print("Received message:", received_msg.data.decode("utf-8"))
                if received_msg.block_index != 0:  # The first block received is not the first block; something must be wrong, probably a lost message
                    pass    # problem
                elif block_num == 1:    # single block
                    resend_flag = 0  # receiving message succeed
                elif block_num != 1:  # multiply blocks
                    # Sets the timeout in seconds
                    server_socket.settimeout(5.0)
                    for i in range(1, block_num):
                        # The subsequent blocks are received one by one
                        msg_block, _ = server_socket.recvfrom(512)
                        msg_block_list.append(msg_block)
                        received_msg = deserialize(msg_block_list[-1])
                        if received_msg.block_index == i:    # right sequence
                            if block_num == received_msg.block_index:  # last block?
                                resend_flag = 0  # all received
                        else:   # wrong sequence
                            resend_flag = 1
                            break

            except socket.timeout:
                print('client timeout, requiring resend')
                resend_flag = 1
            # urge to resend message
            if resend_flag == 1:
                requiring_resend_block = Message(
                    0, 26, 1, 1, "Error: resend the request!")
                server_socket.sendto(serialize(
                    requiring_resend_block), address)
                resend_times += 1
            # receive complete msg
            else:
                original_text, identifier = unmarshalling(msg_block_list)
                # Successfully received the correct information
                request_id = identifier
                operation = original_text
                server_socket.settimeout(0)
                break

        # After receiving the request information, the request is executed
        if operation == "exit":
            # response = "client exit"
            args = operation
        else:
            args = operation.split(',')

        cache_flag = 1
        # In "at-most-once" mode, check request ID to avoid processing duplicate requests
        if semantics == "at-most-once" and (address, request_id) in processed_request_ids:
            print(f"Duplicate request {request_id}, resending cached reply.")
            cache_flag = 0
            for cached_reply in buffer:
                if cached_reply[0] == address and cached_reply[1] == request_id:
                    response = cached_reply[3]
        else:
            # Perform operation

            if args[0] == "read_file":
                response = read_file(args[1], int(args[2]), int(args[3]))
            elif args[0] == "insert_content":
                response = insert_content(args[1], int(args[2]), args[3])
            elif args[0] == "monitor_updates":
                response = "Monitor started"

                msg_list = marshalling(response, 0)
                for msg in msg_list:
                    server_socket.sendto(msg, address)


                monitor_updates(args[1], int(args[2]),address, address_list, server_socket)
            elif args[0] == "file_list":
                response = file_list(args[1])
                if response == "Path error or not found!":
                    pass
                else:
                    response = ','.join(response)
            elif args[0] == "rename_file":
                response = rename_file(args[1], args[2])
            elif args[0] == "exit":
                response == "client exit"
            else:
                response = "Invalid request"

        # Record the processed request ID (only in "at-most-once" mode) and cache the reply
        if semantics == "at-most-once" and cache_flag == 1:
            processed_request_ids.add((address, request_id))
            buffer.append((address, processed_request_ids, marshalling(response, 0)))

        # Send response
        # test for packet loss
        i = random.randint(0, 10)
        if i < 11:
            print(f"Sending response: {response}")
            if response == "exit":
                break
            else:
                msg_list = marshalling(response, 0)
                for msg in msg_list:
                    server_socket.sendto(msg, address)
        else:
            print('test loss of reply')
            pass


if __name__ == "__main__":
    semantic = input("Choose server mode[M/L]:")
    semantic = "at-most-once" if semantic == "M" else semantic == "at-least-once"
    print('Server mode:', semantic)
    start_server(semantic)
