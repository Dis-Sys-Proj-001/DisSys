import socket
import os
from serialization_old import deserialize, serialize, Message, unmarshalling, marshalling
# from serialization import deserialize, serialize, Message, unmarshalling, marshalling


if __name__ == "__main__":

    host = '127.0.0.1'
    addr = (host, 25896)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
    s.bind(addr)
    # s.listen(128)
    print('UDP Server on', addr[0], ":",addr[1],"......")



    while True:
        # c, addr = s.accept()

        # receive requeat
        msg_byte, Caddr = s.recvfrom(512)
        msg_byte_list = [msg_byte]
        request_text, the_identifier = unmarshalling(msg_byte_list)
        print("Received message from:", Caddr)
        print("Request:", request_text)


        # send response
        msg_list = marshalling("========response=======", 333333)
        # msg_list = marshalling("Error: resent the request!", 9999999)
        for item in msg_list:
            # print(len(item))
            s.sendto(item, Caddr)
            print("Sent response back!")
