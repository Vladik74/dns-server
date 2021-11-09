import binascii
from typing import Tuple, List
import socket
from records import AnswerRecord, QueryRecord
from random import choice


def lookup(url: str):
    query = build_query(url)
    current_server_ip = root_server

    while True:
        response = send_udp_message(query, current_server_ip, 53)
        ans, auths, adds = read_response(response)
        if len(ans) != 0:
            return ans
        adds = list(filter(lambda r: r.record_type == "0001", adds))
        # random_auth_address = choice(auths).address
        random_auth_address = auths[0].address
        ip = ''
        for add in adds:
            if random_auth_address == add.name:
                ip = add.address
                break
        if ip:
            current_server_ip = ip
        else:
            current_server_ip = choice(lookup(random_auth_address)).address


def send_udp_message(message, address, port):
    server_address = (address, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(binascii.unhexlify(message), server_address)
        data, _ = sock.recvfrom(4096)
    finally:
        sock.close()
    return binascii.hexlify(data).decode("utf-8")


def build_query(required_address):
    ID = 'AAAA'
    FLAGS = '0000'
    QDCOUNT = '0001'
    ANCOUNT = '0000'
    NSCOUNT = '0000'
    ARCOUNT = '0000'
    headers = ID + FLAGS + QDCOUNT + ANCOUNT + NSCOUNT + ARCOUNT
    domains = required_address.split('.')
    question = ''
    hex_required_address = ''
    for d in domains:
        hex_required_address += format(len(d), '02x') + d.encode('ascii').hex()
    # print(hex_required_address)
    QTYPE = '0001'
    QCLASS = '0001'
    question += hex_required_address + '00' + QTYPE + QCLASS
    return headers + question


def get_url(message: str, start: int, url_len: int = None) -> Tuple[str, int]:
    current_index = start
    url = ''
    while message[current_index: current_index + 2] != '00':
        current_token_len = int(message[current_index: current_index + 2],
                                16) * 2
        if current_token_len >= 384:
            offset = get_offset(message[current_index: current_index + 4]) * 2
            offset_url, _ = get_url(message, offset)
            url += offset_url
            return url, current_index + 4
            # current_index += 4
        else:
            token = message[
                    current_index + 2: current_index + current_token_len + 2]
            decoded_token = bytes.fromhex(''.join(token)).decode('ascii')
            url += decoded_token
            current_index = current_index + current_token_len + 2
        if url_len and current_index == start + url_len:
            break
        if message[current_index: current_index + 2] != '00':
            url += '.'
        else:
            break
    if message[current_index: current_index + 2] == '00':
        current_index += 2
    return url, current_index


def get_offset(hex_num: str):
    return int(hex_num, 16) - int('1100000000000000', 2)


def take(message: str, start: int, count: int) -> Tuple[str, int]:
    return message[start: start + count], start + count


def parse_query(message: str, start: int) -> Tuple[QueryRecord, int]:
    current_index = start
    name, current_index = get_url(message, current_index)
    record_type, current_index = take(message, current_index, 4)
    record_class, current_index = take(message, current_index, 4)
    return QueryRecord(name, record_type), current_index


def parse_answer(message: str, start: int) -> Tuple[AnswerRecord, int]:
    current_index = start
    encoded_offset, current_index = take(message, current_index, 4)
    offset = get_offset(encoded_offset) * 2
    name, _ = get_url(message, offset)
    record_type, current_index = take(message, current_index, 4)
    record_class, current_index = take(message, current_index, 4)
    ttl, current_index = take(message, current_index, 8)
    data_length, current_index = take(message, current_index, 4)
    data_length = int(data_length, 16)
    if record_type == '0001' or record_type == '001c':
        address, current_index = take(message, current_index,
                                      data_length * 2)
    else:
        address, current_index = get_url(message, current_index,
                                         data_length * 2)
    # print(bytes.fromhex(address).decode('ascii'))

    return AnswerRecord(name, record_type, int(ttl, 16), address), current_index


def decode_ip(address: str, record_type: str):
    if record_type == "0001":
        token_list = [int(address[i:i + 2], 16) for i in
                      range(0, len(address), 2)]
        ip = ".".join(map(str, token_list))
    else:
        token_list = [address[i:i + 4] for i in range(0, len(address), 4)]
        ip = ":".join(token_list)
    return ip


def read_response(response) -> Tuple[List[AnswerRecord], List[AnswerRecord],
                                     List[AnswerRecord]]:
    ind = 0
    transaction_id, ind = take(response, ind, 4)
    flags, ind = take(response, ind, 4)
    # if flags != '8000':
    #     raise ConnectionError("There are some problems with server access")
    questions_number, ind = take(response, ind, 4)
    answers_number, ind = take(response, ind, 4)
    authority_number, ind = take(response, ind, 4)
    additional_number, ind = take(response, ind, 4)

    questions = []
    for i in range(int(questions_number, 16)):
        question, ind = parse_query(response, ind)
        questions.append(question)

    answers = []
    for i in range(int(answers_number, 16)):
        answer, ind = parse_answer(response, ind)
        ip = decode_ip(answer.address, answer.record_type)
        answer.address = ip
        answers.append(answer)

    authoritives = []
    for i in range(int(authority_number, 16)):
        authoritive, ind = parse_answer(response, ind)
        authoritives.append(authoritive)

    additionals = []
    for i in range(int(additional_number, 16)):
        additional, ind = parse_answer(response, ind)
        ip = decode_ip(additional.address, additional.record_type)
        additional.address = ip
        additionals.append(additional)

    print('ANSWERS')
    print(*answers, sep='\n')

    print('AUTHORITIVES')
    print(*authoritives, sep='\n')

    print('ADDITIONALS')
    print(*additionals, sep='\n')

    return answers, authoritives, additionals


if __name__ == "__main__":
    root_server = "199.7.83.42"
    required_address = input()
    answers = lookup(required_address)
    print(answers, sep='\n')
