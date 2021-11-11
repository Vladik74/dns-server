class AnswerRecord:
    def __init__(self, name: str, record_type: str, ttl: int, address: str,
                 end_index: int, message=None, death_time=None):
        self.name = name
        self.record_type = record_type
        self.ttl = ttl
        self.address = address
        self.end_index = end_index
        self.message = message
        self.death_time = death_time


    def __repr__(self):
        return (f'AnswerRecord(name={self.name}, '
                f'record_type={self.record_type}, '
                f'ttl={self.ttl}, '
                f'address={self.address},'
                f'death_time={self.death_time})')

    def __str__(self):
        return repr(self)


class QueryRecord:
    def __init__(self, name: str, record_type: str, end_index: int):
        self.name = name
        self.record_type = record_type
        self.end_index = end_index

    def __repr__(self):
        return (f'QueryRecord(name={self.name}, '
                f'record_type={self.record_type})')

    def __str__(self):
        return repr(self)
