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
    except (FileNotFoundError , NotADirectoryError):
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


def start_server(semantics, server_addr):
    # Create a UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(server_addr)
    print('UDP Server on', server_addr[0], ":", server_addr[1], "......")

    # Store processed request IDs for deduplication (only used in "at-most-once" mode)
    processed_request_ids = set()
    # Store all addresses of clients requiring monitor
    address_list = []
    # Store past reply message
    cache = []

    while True:
        resend_flag = 1  # Resend flag, if 1 in the end, there is a reception error
        resend_times = 0
        while resend_flag == 1 and resend_times < 10:
            # sending timeout is set via socket's timeout settings
            server_socket.setblocking(True)
            try:
                # get the first block
                msg_byte, address = server_socket.recvfrom(512)
                msg_byte_list = [msg_byte]
                msg_rev_obj = deserialize(msg_byte_list[0])
                block_num = msg_rev_obj.total_blocks
                print("Received message:", msg_rev_obj.data.decode("utf-8"))

                if msg_rev_obj.block_index == 0:        # first block received is not the first block in message
                    if block_num == 1:                  # single block
                        resend_flag = 0                 # All blocks received!
                    elif block_num != 1:                # multiple blocks
                        server_socket.settimeout(5.0)   # Set the timeout in seconds
                        for i in range(1, block_num):   # get subsequent blocks sequentially
                            msg_byte, _ = server_socket.recvfrom(512)
                            msg_byte_list.append(msg_byte)
                            msg_rev_obj = deserialize(msg_byte_list[-1])
                            if msg_rev_obj.block_index == i:              # right sequence
                                if block_num == msg_rev_obj.block_index:  # last block?
                                    resend_flag = 0     # All blocks received!
                            else:                       # wrong sequence
                                resend_flag = 1
                                break
                else:       # first block received is not the first block in message
                    resend_flag = 1
            except socket.timeout:                      # timeout when receiving messages
                print('client timeout, requiring resend')
                resend_flag = 1
            # Full message received, unmarshalling and hash test
            try:
                original_text, identifier = unmarshalling(msg_byte_list)
                if original_text == False:  # hash test failed
                    resend_flag = 1
            except Exception:               # exceptions in unmarshalling
                resend_flag = 1

            # urge to resend message
            if resend_flag == 1:
                requiring_resend_block = Message(0, 26, 1, 1, "Error: resend the request!")
                server_socket.sendto(serialize(requiring_resend_block), address)
                resend_times += 1
            # correct message successfully received
            else:
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
            for cached_reply in cache:
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
            cache.append((address, processed_request_ids, marshalling(response, 0)))

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

    server_addr = ('localhost', 2222)
    # server_addr = ('192.168.0.243', 2222)

    semantic = input("Choose server mode[M/L]:")
    semantic = "at-most-once" if semantic == "M" else "at-least-once"
    print('Server mode:', semantic)
    start_server(semantic,server_addr)
