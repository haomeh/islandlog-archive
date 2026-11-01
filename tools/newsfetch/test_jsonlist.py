"""T82b: iter_list accepts what json.load accepts and rejects what json.load rejects, at each block size (T82-V opus G1, G2)."""
import json
import os
import tempfile
import unittest

from tools.newsfetch import jsonlist

GOOD = [
    "[]", " [ ] \n", "[1]", "[12,345]", "[12, 345, 6789]", "[1e5, 2.5e+3, -0.5, 1E-2, 0, -0, 10.25]",
    "[true,false,null]", '["a","b,c","]"]', '[{"a":1},{"b":[1,2,{"c":"]"}]}]', "[\n1\n,\n2\n]\n", '["中文", 12345]',
    "[NaN, Infinity, -Infinity]", "\t[1,\r\n2]\t\r\n", '[[1,2],[3,[4]],{"k":12}]',
]
# The forms that the T82-V reports name (G1, G2), and more damaged forms.
BAD = [
    "[1 2]", "[1,,2]", "[,]", "[1,]", "[1,2,]", "[,1]", '[{"a":1}{"b":2}]', "[] x", "[]   x", "[1] 2", "[1]]", "[1],", "[1,2",
    "[", "", "   ", "[1 ]x", "[1,\n]", "[1,2]\n,", "[true false]", "[tru]", '["a" "b"]', "[01]", "[1.]", "[-]", "[1e]",
]
BLOCKS = (1, 2, 3, 4, 5, 7, 16, 1 << 22)


def lists_from(text, block):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "x.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return jsonlist.read_list(path, None, block)


class StrictListTest(unittest.TestCase):
    def test_a_good_file_gives_what_json_load_gives_at_each_block_size(self):
        for text in GOOD:
            want = json.loads(text)
            for block in BLOCKS:
                with self.subTest(text=text, block=block):
                    got = lists_from(text, block)
                    self.assertEqual(repr(got), repr(want))  # repr: NaN equals itself

    def test_a_bad_file_raises_ValueError_at_each_block_size(self):
        for text in BAD:
            with self.assertRaises(ValueError):
                json.loads(text)
            for block in BLOCKS:
                with self.subTest(text=text, block=block):
                    with self.assertRaises(ValueError):
                        lists_from(text, block)

    def test_a_file_that_is_not_a_list_raises_ValueError(self):
        for text in ("{}", "12", '"a"', "null", "{\"a\":[1]}"):
            for block in BLOCKS:
                with self.subTest(text=text, block=block):
                    with self.assertRaises(ValueError):
                        lists_from(text, block)

    def test_a_number_is_not_split_at_a_block_end(self):
        self.assertEqual(lists_from("[12,345]", 3), [12, 345])
        self.assertEqual(lists_from("[12,345]", 2), [12, 345])
        self.assertEqual(lists_from("[1e5,2]", 2), [100000.0, 2])
        self.assertEqual(lists_from("[1.5e+10]", 4), [1.5e10])


if __name__ == "__main__":
    unittest.main()
