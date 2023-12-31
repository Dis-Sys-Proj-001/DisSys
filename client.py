import random
import socket
import time
from serialization import deserialize, serialize, Message, unmarshalling, marshalling

# Funcitons list
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
    if i < 11:  # packet loss disabled
        msg_list = marshalling(request_msg, identifier)
        for item in msg_list:
            socket1.sendto(item, server_addr)
    else:
        print('test loss of request')


def receive_message(socket1: socket, server_addr, timeout=10):
    resend_flag = 1  # Resend flag, if 1 in the end, there is a reception error
    resend_times = 0
    while resend_flag == 1 and resend_times < 10:
        # sending timeout is set via socket's timeout settings
        socket1.settimeout(timeout)
        try:
            # get the first block
            msg_byte, Saddr = socket1.recvfrom(512)
            msg_byte_list = [msg_byte, ]
            msg_rev_obj = deserialize(msg_byte_list[0])
            block_num = msg_rev_obj.total_blocks
            if msg_rev_obj.block_index == 0:        # first block received is not the first block in message
                # single block message
                if block_num == 1:
                    resend_flag = 0                 # All blocks received!
                # multiple block message
                elif block_num != 1:
                    for i in range(1, block_num):   # get subsequent blocks sequentially
                        msg_byte, Saddr1 = socket1.recvfrom(512)
                        msg_byte_list.append(msg_byte)
                        msg_rev_obj = deserialize(msg_byte_list[-1])
                        if msg_rev_obj.block_index == i:                # new block is in the right sequence
                            if block_num == msg_rev_obj.block_index:    # lastblock?
                                resend_flag = 0     # All blocks received!
                        else:                       # wrong sequence
                            resend_flag = 1
                            break
            else:       # first block received is not the first block in message
                resend_flag = 1
        except socket.timeout:                      # timeout when receiving messages
            print("Receive operation timed out")
            resend_flag = 1
        # Full message received, unmarshalling and hash test
        try:
            original_text, the_identifier = unmarshalling(msg_byte_list)
            if original_text == False:  # hash test failed
                resend_flag = 1
        except Exception:               # exceptions in unmarshalling
            resend_flag = 1

        # Resend message
        if resend_flag == 1:
            resend_times = resend_times + 1
            print("Error! Resent the request")
            original_text = "Error: resend the request!"
            the_identifier = 0
            break

    # Message successfully received
    socket1.setblocking(0)
    return original_text, the_identifier


def echo_response(msg_list, response_text):
    # function_name = options[msg_list[0]]['function_name']
    function_name = msg_list[0]

    if function_name == 'read_file':
        # content = response_text.split("$")
        print("Read success! The contents of the file are as follows:")
        # print(content.decode('utf-8'))
        offset = int(msg_list[2])
        length_to_read = int(msg_list[3])
        text = response_text
        text1 = text[offset:offset+length_to_read]
        print(text1)

    elif function_name == 'insert_content':
        if response_text == "Insertion successful":
            print("Successful insertion")
        else:
            print("Fail insertion: ", response_text)

    elif function_name == 'monitor_updates':
        pass    # elsewhere

    elif function_name == 'file_list':
        if response_text == "Path error or not found!":
            print("Failed to list files:   Path error or not found!")
        else:
            print("file list: ")
            print(response_text)

    elif function_name == 'rename_file':
        if response_text == "Rename successful":
            print("Rename successful!")
        else:
            print("Rename unsuccessful: ", response_text)

    else:
        print("unknown operation: ", function_name)
        print("response: ", response_text)


def get_parameters(num_params):
    parameters = []
    for i in range(num_params):
        param = input(f"parameter {i+1}: ")
        parameters.append(param)
    return parameters


def start_Client(server_addr=('127.0.0.1', 25896), freshness_interval=10, semantics="at_least_once"):
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    identifier = 0
    read_buffer = {}
    cache_list = []
    # terminal interacting panel
    while True:
        print("\n==============function list=================")
        for k, v in options.items():
            print(f"{k}. {v['display_name']}")
        choice = input(
            "Please select the function you want to use and enter the serial number(1-7): ")
        # Exit
        if choice == "7":
            print("Successfully exited!")
            break

        # Get parameters
        if choice in options:
            print(f"perform function: {options[choice]['display_name']}")
            num_params = options[choice]['params']
            parameters = get_parameters(num_params)

            if choice == "1":   # read function, use cache
                
                # cache_list: [file_name, validated_time, modified_time, full_file]
                file_name = parameters[0]
                msg_list = [options[choice]['function_name']] + parameters

                # check whether file is in the cache 
                cached_file = next((item for item in cache_list if item[0] == file_name), None)
                current_time = time.time()
                # cache spotted:
                if cached_file:
                    print("***cache spotted!***")
                    modified_time = cached_file[1]

                    # check whether cache is valid, using freshness_interval
                    if time.time() - modified_time <= freshness_interval:
                        respond_msg = cached_file[3]
                        print("***cache used!***")
                        echo_response(msg_list, respond_msg)
                        continue
                    else:
                        # update modified_time
                        msg_list1 = ["get_modified_time",file_name]
                        request_msg = f"{','.join(msg_list1)}"
                        identifier = (identifier + 1)% 256
                        send_message(c, server_addr, request_msg, identifier)
                        print("***modified_time requested!***")
                        modified_time_new, _ = receive_message(c, server_addr, timeout=100)
                        print("***modified_time got!***")
                        

                        if float(modified_time_new) == float(cached_file[2]):  # file didn't change
                            print("***modified_time same, still use cache!***")
                            cached_file[1] = current_time
                            # still use cache
                            respond_msg = cached_file[3]
                            print("***cache used!***")
                            echo_response(msg_list, respond_msg)
                            continue
                        else:   # file changed
                            print("**modified_time changed, cache expired!**")
                            cache_list.remove(cached_file)
                            pass
                else:           # not in cache 
                    pass        # requeat normally






                # result = read_buffer.get(tuple(parameters))
                # # not cached
                # if result == None:
                #     pass    # normal read request
                # else:
                #     [response, cached_time] = result
                #     print("***cache spotted!**")
                #     if time.time() - cached_time <= freshness_interval:
                #         print("***cache used!***")
                #         msg_list = [options[choice]['function_name']] + parameters
                #         echo_response(msg_list, response)
                #         continue    # end request, goto next input
                #     else:
                #         print("**Sorry, cache expired!**")

            # Generate request message
            if choice == "6":   # manually input
                msg_list = parameters
            else:
                msg_list = [options[choice]['function_name']] + parameters
            request_msg = f"{','.join(msg_list)}"
            print("Request message: ", request_msg)

            # Send request message
            identifier = (identifier + 1) % 256
            success = 0
            while success != 1:
                send_message(c, server_addr, request_msg, identifier)
                print("-Request: \n", request_msg, "\n-Sent!")

                # Receive answer
                response_text, _ = receive_message(c, server_addr, 5)
                # resend
                if response_text == "Error: resend the request!":
                    success = 0
                    print("Request/Reply error, retransmission......")
                # successfully received response
                else:
                    success = 1
                    # print("Received response:", response_text)

                    # Action after receiving
                    if choice == "1":   # Read something new. Update the cache
                        # update cache
                        if response_text != "File does not exist!":
                            modified_time, full_file = response_text.split('$')
                            cache_list.append([file_name, time.time(), modified_time, full_file])
                            print("cache:\n", cache_list)
                            echo_response(msg_list, full_file)
                        else:
                            echo_response(msg_list, response_text)

                    elif choice == "3":  # Listening for updates
                        if response_text == "Monitor started":
                            if 1 == 1:
                                print("Start listening. Listening", msg_list[2], "s")
                                # Set the socket to non-blocking mode
                                c.setblocking(0)
                                start_time = time.time()
                                while time.time() - start_time < (float(msg_list[2])+10.0):
                                    try:
                                        data1, Saddr = receive_message(
                                            c, server_addr, 65536)
                                        print("Received data:", data1, "from", Saddr)
                                        print("Updated file: \n", data1)
                                        data1 = ""
                                    except socket.error:
                                        # No data is coming. Keep waiting
                                        pass
                        else:
                            print("Monitor didn't started!")
                    else:
                        echo_response(msg_list, response_text)
        else:   # choice input is not in selection list
            print("Invalid selection, please re-enter!")
    return c



if __name__ == "__main__":

    # server_addr = ('139.9.246.66', 2222)
    server_addr = ('127.0.0.1', 2222)

    c = start_Client(server_addr, 10, "at-most-once")
