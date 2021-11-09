class AnswerRecord:
    def __init__(self, name: str, record_type: str, ttl: int, address: str):
        self.name = name
        self.record_type = record_type
        self.ttl = ttl
        self.address = address

    def __repr__(self):
        return (f'AnswerRecord(name={self.name}, '
                f'record_type={self.record_type}, '
                f'ttl={self.ttl}, '
                f'address={self.address})')

    def __str__(self):
        return repr(self)


class QueryRecord:
    def __init__(self, name: str, record_type: str):
        self.name = name
        self.record_type = record_type

    def __repr__(self):
        return (f'QueryRecord(name={self.name}, '
                f'record_type={self.record_type})')

    def __str__(self):
        return repr(self)
