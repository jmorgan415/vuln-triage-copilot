import unittest

from sqlparse.exceptions import SQLParseError

from app.query_log import normalize_query


class NormalizeQueryTest(unittest.TestCase):
    def test_support_console_snippet_is_normalized(self):
        raw = "select /* customer-reported slow query */ * from transactions where merchant_id = ?"
        self.assertEqual(
            normalize_query(raw),
            "SELECT *\nFROM transactions\nWHERE merchant_id = ?",
        )

    def test_keywords_uppercased_and_comments_stripped(self):
        out = normalize_query("select id from payments -- trailing note\nwhere amount_cents > 100")
        self.assertNotIn("trailing note", out)
        self.assertIn("SELECT id", out)
        self.assertIn("WHERE amount_cents > 100", out)

    def test_deeply_nested_input_fails_cleanly(self):
        # CVE-2024-4340: pre-0.5 sqlparse hit RecursionError on deep nesting.
        with self.assertRaises(SQLParseError):
            normalize_query("SELECT " + "(" * 5000 + "1" + ")" * 5000)


if __name__ == "__main__":
    unittest.main()
