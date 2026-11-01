"""Reads a JSON file whose top level is a list, one element at a time (T82). Standard library only.

json.load holds the text of the whole file as one string (4 bytes a character for a file with CJK text) next to the parsed value.
iter_list holds one block and one element. An object_hook can reduce each object while it is read.
The grammar is the one of json.load (T82b): one comma between two elements, no comma before "]", no text after "]"."""
import json

WHITE = " \t\r\n"  # the white space of JSON
NUMBER_TAIL = 3  # "e+5" is the longest part that can follow a number that a block end cut


def iter_list(path, object_hook=None, block=1 << 22):
    """Yield the elements of the list in the file, as json.load gives them (reduced by object_hook when given).
    A file that json.load rejects, or whose top level is not a list, raises ValueError."""
    decoder = json.JSONDecoder(object_hook=object_hook)
    with open(path, encoding="utf-8") as f:
        buf, pos, eof = "", 0, False

        def fill():
            """Read one more block; keep the text from pos on. False at the end of the file."""
            nonlocal buf, pos, eof
            if eof:
                return False
            more = f.read(block)
            if not more:
                eof = True
                return False
            buf, pos = buf[pos:] + more, 0
            return True

        def skip():
            """Skip white space. True when a character is at pos, False at the end of the file."""
            nonlocal pos
            while True:
                while pos < len(buf) and buf[pos] in WHITE:
                    pos += 1
                if pos < len(buf):
                    return True
                if not fill():
                    return False

        if not skip() or buf[pos] != "[":
            raise ValueError("the top level of the file is not a list")
        pos += 1
        if not skip():
            raise ValueError("the list does not end")
        first = True
        while True:
            if buf[pos] == "]" and first:
                pos += 1
                break
            first = False
            if buf[pos] in "],":
                raise ValueError("a value is missing in the list")
            while True:
                try:
                    value, end = decoder.raw_decode(buf, pos)
                except json.JSONDecodeError:
                    if not fill():
                        raise
                    continue
                # a block end can cut a number: "12" of "123", "1" of "1e5" (T82b); read on until the number has its end
                if isinstance(value, (int, float)) and len(buf) - end < NUMBER_TAIL and fill():
                    continue
                break
            yield value
            pos = end
            if not skip():
                raise ValueError("the list does not end")
            mark = buf[pos]
            pos += 1
            if mark == "]":
                break
            if mark != ",":
                raise ValueError("a comma or the end of the list is missing")
            if not skip():
                raise ValueError("the list does not end")
        if skip():
            raise ValueError("text after the list")


def read_list(path, object_hook=None, block=1 << 22):
    return list(iter_list(path, object_hook, block))
