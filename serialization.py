import struct
import hashlib
BLOCK_SIZE = 496

class Message:
    def __init__(self, identifier, length, block_index, total_blocks, data):
        self.identifier = identifier
        self.length = length
        self.block_index = block_index
        self.total_blocks = total_blocks
        self.data = data

def serialize(msg):
    # Encapsulate the message as a bytes object
    fmt = f'I I I I {BLOCK_SIZE}s'  # Create formatted string
    packed_data = struct.pack(fmt, msg.identifier, msg.length, msg.block_index, msg.total_blocks, msg.data.encode('utf-8'))
    return packed_data

def deserialize(packed_data):
    # Unpack the bytes object into a message object
    fmt = f'I I I I {BLOCK_SIZE}s'
    print("deserialize in process!")
    unpacked_data = struct.unpack(fmt, packed_data)
    modified_data = unpacked_data[:-1] + (unpacked_data[-1] + b'\0',)
    return Message(*modified_data)

def test():
    # single block test
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
    hash_value = hashlib.md5(LargeText.encode("utf-8")).hexdigest() # integrity check
    for block_index in range(total_block-1):
        start_index = block_index * BLOCK_SIZE
        end_index = start_index + BLOCK_SIZE
        block_data = LargeText[start_index:end_index]
        msg = Message(identifier,len(block_data), block_index, total_block, block_data)
        marshalled_data = serialize(msg)
        marshalling_block.append(marshalled_data)
    hash_msg = Message(identifier, len(hash_value), total_block-1, total_block, hash_value)
    marshalled_data = serialize(hash_msg)
    marshalling_block.append(marshalled_data)
    return marshalling_block

def unmarshalling(marshalling_block):
    list = []
    for marshalled_data in marshalling_block:
        msg = deserialize(marshalled_data)
        list.append(msg)
    identifier = list[0].identifier
    total_num = list[0].total_blocks
    text = []
    for index, i in enumerate(list):
        if index == i.block_index and index < total_num-1:
            temp1_text = i.data.rstrip(b'\0').decode("utf-8")
            text.append(temp1_text)
        elif index == total_num-1:
            pass
        else:
            return False, identifier
        res = "".join([str(i) for i in text])
    # Check whether the hash is consistent. If it is inconsistent, the value returns False and identifier.
    if hashlib.md5(res.encode("utf-8")).hexdigest() == list[total_num-1].data.rstrip(b'\0').decode("utf-8"):
        return res, identifier
    else:
        print("hash not fix!")
        return False, identifier


if __name__ == "__main__":
    ## Marshalling requires two parameters, the string to be sent and the identifier
    text = input("input") # any string
    identifier = 4444444 #
    byte_arrays = marshalling(text, identifier) # after marshalling, it is a bit stream, sent through the socket
    print(len(byte_arrays))
    print(len(byte_arrays[0]))
    print("Byte stream is: ",byte_arrays)

    ## one parameter, i.e. the received bit stream
    original_text, the_identifier = unmarshalling(marshalling_block=byte_arrays) # return original text and its identifier
    print("Initial text is: ",original_text)
    print("identifier:",the_identifier)

    ## fault torlerance:
    # original_text, the_identifier = unmarshalling(marshalling_block=byte_arrays) # 如果有误， original_text将会是False
    if original_text != False:
        pass # normal...
    else:
        print("something wrong")
        pass # faulty...