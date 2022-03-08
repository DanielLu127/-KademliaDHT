import operator
import time
from collections import OrderedDict


class ForgetfulStorage():
    def __init__(self, ttl=604800):
        self.data = OrderedDict()
        self.ttl = ttl

    def __setitem__(self, key, value):
        if key in self.data:
            del self.data[key]
        self.data[key] = (time.monotonic(), value)
        self.cull()

    # remove expired data
    def cull(self):
        for _, _ in self.iter_older_than(self.ttl):
            self.data.popitem(last=False)

    def __getitem__(self, item):
        self.cull()
        return self.data[item][1]

    def get(self, key, default=None):
        self.cull()
        if key in self.data:
            return self[key]
        return default

    def __repr__(self):
        self.cull()
        return repr(self.data)

    def iter_older_than(self, seconds_old):
        min_birthday = time.monotonic() - seconds_old
        ikeys = self.data.keys()
        ibirthdays = []
        for item in self.data.values():
            ibirthdays.append(item[0])

        ivalues = []
        for item in self.data.values():
            ivalues.append(item[1])

        zipped = zip(ikeys, ibirthdays, ivalues)
        matches = []

        for item in zipped:
            if item[1] <= min_birthday:
                matches.append(item)
            else:
                break

        return list(map(operator.itemgetter(0, 2), matches))

    def __iter__(self):
        self.cull()
        ikeys = self.data.keys()
        ivalues = map(operator.itemgetter(1), self.data.values())
        return zip(ikeys, ivalues)

