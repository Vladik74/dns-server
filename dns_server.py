import binascii
from os import path
from typing import Tuple, List
import socket
from records import AnswerRecord, QueryRecord
from random import choice
import datetime
import pickle


def send_udp_message(message, address):
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
    return QueryRecord(name, record_type, current_index), current_index


def parse_answer(message: str, start: int) -> Tuple[AnswerRecord, int]:
    name, current_index = get_url(message, start)
    record_type, current_index = take(message, current_index, 4)
    record_class, current_index = take(message, current_index, 4)
    ttl, current_index = take(message, current_index, 8)
    data_length, current_index = take(message, current_index, 4)
    data_length = int(data_length, 16)
    if record_type == '0001' or record_type == '001c':
        address, current_index = take(message, current_index, data_length * 2)
    else:
        address, current_index = get_url(message, current_index,
                                         data_length * 2)
    return AnswerRecord(name, record_type, int(ttl, 16), address,
                        current_index), current_index


def decode_ip(address: str, record_type: str):
    if record_type == "0001":
        token_list = [int(address[i:i + 2], 16) for i in
                      range(0, len(address), 2)]
        ip = ".".join(map(str, token_list))
    else:
        token_list = [address[i:i + 4] for i in range(0, len(address), 4)]
        ip = ":".join(token_list)
    return ip


def read_response(response) -> Tuple[List[QueryRecord],
                                     List[AnswerRecord], List[AnswerRecord],
                                     List[AnswerRecord]]:
    ind = 0
    transaction_id, ind = take(response, ind, 4)
    flags, ind = take(response, ind, 4)
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

    for answer in answers:
        write_to_cache(answer)

    return questions, answers, authoritives, additionals


def lookup(message: str, is_url=False):
    current_server_ip = root_server
    if is_url:
        message = build_query(message)

    while True:
        response = send_udp_message(message, current_server_ip)
        quests, ans, auths, adds = read_response(response)
        if len(ans) != 0:
            return ans if is_url else response
        adds = list(filter(lambda r: r.record_type == "0001", adds))
        random_auth_address = choice(auths).address
        ip = ''
        for add in adds:
            if random_auth_address == add.name:
                ip = add.address
                break
        if ip:
            current_server_ip = ip
        else:
            current_server_ip = choice(
                lookup(random_auth_address, is_url=True)).address


def write_to_cache(answer: AnswerRecord):
    answer.death_time = (datetime.datetime.now() +
                         datetime.timedelta(seconds=answer.ttl))
    with open("cache.pickle", 'rb') as cache:
        current_cache = pickle.load(cache)
    current_cache.append(answer)
    with open("cache.pickle", 'wb') as cache:
        pickle.dump(current_cache, cache)


def check_cache(url: str):
    if not path.exists("cache.pickle"):
        with open("cache.pickle", 'wb') as w_cache:
            pickle.dump([], w_cache)
    else:
        with open("cache.pickle", 'rb') as r_cache:
            current_time = datetime.datetime.now()
            current_cache = pickle.load(r_cache)
            for c in current_cache:
                if c.name == url:
                    if current_time > c.death_time:
                        current_cache.remove(c)
        with open("cache.pickle", 'wb') as w_cache:
            pickle.dump(current_cache, w_cache)


if __name__ == "__main__":
    root_server = '199.7.83.42'
    port = 53
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(('127.0.0.1', port))
        while True:
            data, addr = s.recvfrom(1024)
            response = binascii.hexlify(data).decode()
            quests, ans, auths, adds = read_response(response)
            query = quests[-1]
            query_end_index = query.end_index
            requested_url = query.name
            check_cache(requested_url)
            r = response[:24]
            new_response = response[:20] + '0000' + response[24:]
            send_data = lookup(new_response)
            # print(send_data, sep='\n')
            # print('\n' * 2)
            # with open("cache.pickle", 'rb') as cache:
            #     print(pickle.load(cache))
            s.sendto(bytes.fromhex(send_data), addr)
