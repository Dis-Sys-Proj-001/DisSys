# -*- coding = utf-8 -*-
# @Time : 2023/10/24 22:53
# @Author:
# @File : serialization.py
# @software: PyCharm

import struct

BLOCK_SIZE = 496

class Message:
    def __init__(self, identifier, length, block_index, total_blocks, data):
        self.identifier = identifier
        self.length = length
        self.block_index = block_index
        self.total_blocks = total_blocks
        self.data = data

def serialize(msg):
    # 封装消息为一个字节对象
    fmt = f'I I I I {BLOCK_SIZE}s'  # 创建格式字符串
    packed_data = struct.pack(fmt, msg.identifier, msg.length, msg.block_index, msg.total_blocks, msg.data.encode('utf-8'))
    return packed_data

def deserialize(packed_data):
    # 解封装字节对象为一个消息对象
    fmt = f'I I I I {BLOCK_SIZE}s'
    # print("dddddddddddddddddddddddddddd",len(packed_data))
    
    unpacked_data = struct.unpack(fmt, packed_data)
    modified_data = unpacked_data[:-1] + (unpacked_data[-1] + b'\0',)
    return Message(*modified_data)

def test():
    #单个block ce shi
    input_msg = input("Enter for a test(less than 256):")
    input_msg_len = len(input_msg)
    date_type = 1 if not input_msg.isdigit() else 2
    msg = Message(date_type, input_msg_len, 0, 1, input_msg)

    serialized_data = serialize(msg)
    deserialized_msg = deserialize(serialized_data)
    data = deserialized_msg.data.rstrip(b'\0')

    print(f'Type: {deserialized_msg.identifier}, Length: {deserialized_msg.length}, Data: {data.decode("utf-8")}')

def marshalling(LargeText, identifier):
    total_block = (len(LargeText) + BLOCK_SIZE - 1) // BLOCK_SIZE
    marshalling_block = []

    for block_index in range(total_block):
        start_index = block_index * BLOCK_SIZE
        end_index = start_index + BLOCK_SIZE
        block_data = LargeText[start_index:end_index]
        msg = Message(identifier,len(block_data), block_index, total_block, block_data)
        marshalled_data = serialize(msg)
        marshalling_block.append(marshalled_data)
    return marshalling_block

def unmarshalling(marshalling_block):
    list = []
    for marshalled_data in marshalling_block:
        msg = deserialize(marshalled_data)
        list.append(msg)
    identifier = list[0].identifier
    text = []
    for index, i in enumerate(list):
        if index == i.block_index:
            temp1_text = i.data.rstrip(b'\0').decode("utf-8")
            text.append(temp1_text)
        else:
            return False
        res = "".join([str(i) for i in text])
    return res, identifier


if __name__ == "__main__":
    """
    调用测试，，，
        """
    ## marshalling需要两个参数，要发送的字符串与identifier
    text = input("input") # 任意字符串传入
    identifier = 4444444 #
    byte_arrays = marshalling(text, identifier) # marshalling后，是比特流，通过socket发送
    print(len(byte_arrays))
    print(len(byte_arrays[0]))
    print("比特流是：",byte_arrays)

    ## 一个参数，既 收到的比特流
    original_text, the_identifier = unmarshalling(marshalling_block=byte_arrays) #返回 原字符串及其identifier
    print("最初文本是",original_text)
    print("identifier:",the_identifier)