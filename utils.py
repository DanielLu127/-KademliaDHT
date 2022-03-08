import hashlib
import operator
import asyncio


def digest(string):
    if not isinstance(string, bytes):
        string = str(string).encode('utf8')
    return hashlib.sha1(string).digest()

def shared_prefix(args):
    prefix = args[0]
    
    i = 1
    while i < len(args):
        index = 0
        while index < min(len(prefix), len(args[i])):
            if (prefix[index] == args[i][index]):
                index += 1
            else:
                break
        prefix = prefix[:index]
        i += 1
    
    return prefix

def bytes_to_bit_string(bites):
    bits = ['{0:08b}'.format(bite) for bite in bites]
    return "".join(bits)

async def gather_dict(dic):
    cors = list(dic.values())
    results = await asyncio.gather(*cors)
    return dict(zip(dic.keys(), results))

def main():
    arr = [100, 200]
    print(bytes_to_bits_string(arr))

if __name__ == "__main__":
    main()