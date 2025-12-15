from django.test import TestCase
import random
from core.tests.tools import compare_dicts

class CompareDictsTest(TestCase):

    def test_equal_simple_dicts(self):
        d1 = {"a": 1, "b": "x", "c": True}
        d2 = {"a": 1, "b": "x", "c": True}

        result, msg = compare_dicts(d1, d2)

        self.assertTrue(result)
        self.assertEqual(msg, "OK")

    def test_empty_dicts(self):
        result, msg = compare_dicts({}, {})

        self.assertTrue(result)
        self.assertEqual(msg, "OK")

    # ---------- KEY DIFFERENCES ----------

    def test_missing_key_in_second(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"a": 1}

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("key 'b' missing in second dict", msg)

    def test_extra_key_in_second(self):
        d1 = {"a": 1}
        d2 = {"a": 1, "b": 2}

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("extra key 'b' in second dict", msg)

    # ---------- TYPE MISMATCH ----------

    def test_value_type_mismatch(self):
        d1 = {"a": 1}
        d2 = {"a": "1"}

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("type mismatch", msg)

    def test_nested_type_mismatch(self):
        d1 = {"a": {"b": 1}}
        d2 = {"a": ["b", 1]}

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("root.a: type mismatch", msg)

    # ---------- VALUE DIFFERENCES ----------

    def test_simple_value_difference(self):
        d1 = {"a": 1}
        d2 = {"a": 2}

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("value mismatch (1 != 2)", msg)

    def test_none_vs_value(self):
        d1 = {"a": None}
        d2 = {"a": 0}

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("type mismatch", msg)

    # ---------- NESTED STRUCTURES ----------

    def test_deep_nested_dict(self):
        d1 = {"a": {"b": {"c": {"d": 1}}}}
        d2 = {"a": {"b": {"c": {"d": 1}}}}

        result, msg = compare_dicts(d1, d2)

        self.assertTrue(result)
        self.assertEqual(msg, "OK")

    def test_deep_nested_value_difference(self):
        d1 = {"a": {"b": {"c": {"d": 1}}}}
        d2 = {"a": {"b": {"c": {"d": 2}}}}

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("root.a.b.c.d", msg)

    # ---------- LISTS & TUPLES ----------

    def test_list_equal(self):
        d1 = {"a": [1, 2, 3]}
        d2 = {"a": [1, 2, 3]}

        result, msg = compare_dicts(d1, d2)

        self.assertTrue(result)

    def test_list_length_mismatch(self):
        d1 = {"a": [1, 2]}
        d2 = {"a": [1, 2, 3]}

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("length mismatch", msg)

    def test_list_item_difference(self):
        d1 = {"a": [1, 2, 3]}
        d2 = {"a": [1, 2, 4]}

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("root.a[2]", msg)

    def test_tuple_comparison(self):
        d1 = {"a": (1, 2)}
        d2 = {"a": (1, 2)}

        result, msg = compare_dicts(d1, d2)

        self.assertTrue(result)

    def test_list_vs_tuple_type_mismatch(self):
        d1 = {"a": [1, 2]}
        d2 = {"a": (1, 2)}

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("type mismatch", msg)

    # ---------- SETS ----------

    def test_sets_equal(self):
        d1 = {"a": {1, 2, 3}}
        d2 = {"a": {3, 2, 1}}

        result, msg = compare_dicts(d1, d2)

        self.assertTrue(result)

    def test_sets_difference(self):
        d1 = {"a": {1, 2, 3}}
        d2 = {"a": {1, 2, 4}}

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("set mismatch", msg)

    # ---------- MIXED COMPLEX ----------

    def test_complex_structure(self):
        d1 = {
            "a": [
                {"x": 1, "y": [1, 2, 3]},
                {"z": {"k": "v"}}
            ],
            "b": True
        }

        d2 = {
            "a": [
                {"x": 1, "y": [1, 2, 3]},
                {"z": {"k": "v"}}
            ],
            "b": True
        }

        result, msg = compare_dicts(d1, d2)

        self.assertTrue(result)

    def test_complex_structure_difference(self):
        d1 = {
            "a": [
                {"x": 1, "y": [1, 2, 3]},
                {"z": {"k": "v"}}
            ]
        }

        d2 = {
            "a": [
                {"x": 1, "y": [1, 2, 4]},
                {"z": {"k": "v"}}
            ]
        }

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("root.a[0].y[2]", msg)

    # ---------- MULTIPLE DIFFERENCES ----------

    def test_multiple_differences_reported(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"a": "1", "c": 3}

        result, msg = compare_dicts(d1, d2)

        self.assertFalse(result)
        self.assertIn("type mismatch", msg)
        self.assertIn("key 'b' missing", msg)
        self.assertIn("extra key 'c'", msg)