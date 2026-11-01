"""Reads a JSON file whose top level is a list, one element at a time (T82). Standard library only.

json.load holds the text of the whole file as one string (4 bytes a character for a file with CJK text) next to the parsed value.
iter_list holds one block and one element. An object_hook can reduce each object while it is read."""
import json


def iter_list(path, object_hook=None, block=1 << 22):
    """Yield the elements of the list in the file, as json.load gives them (reduced by object_hook when given).
    A file whose top level is not a list raises ValueError."""
    decoder = json.JSONDecoder(object_hook=object_hook)
    with open(path, encoding="utf-8") as f:
        buf = f.read(block)
        pos = len(buf) - len(buf.lstrip())
        if buf[pos:pos + 1] != "[":
            raise ValueError("the top level of the file is not a list")
        pos += 1
        eof = False
        while True:
            while True:  # skip white space and commas; read more when the buffer ends
                while pos < len(buf) and buf[pos] in " \t\r\n,":
                    pos += 1
                if pos < len(buf) or eof:
                    break
                more = f.read(block)
                eof = not more
                buf, pos = buf[pos:] + more, 0
            if pos >= len(buf):
                raise ValueError("the list does not end")
            if buf[pos] == "]":
                if buf[pos + 1:].strip() or f.read(1).strip():
                    raise ValueError("text after the list")
                return
            while True:
                try:
                    value, end = decoder.raw_decode(buf, pos)
                    break
                except json.JSONDecodeError:
                    more = f.read(block)
                    if not more:
                        raise
                    buf, pos = buf[pos:] + more, 0
            yield value
            pos = end


def read_list(path, object_hook=None, block=1 << 22):
    return list(iter_list(path, object_hook, block))
