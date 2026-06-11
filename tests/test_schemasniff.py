import unittest
from schemasniff.main import extract_messages

class TestSchemaSniff(unittest.TestCase):
    def test_extract_messages_dict(self):
        data = {"message": "error here", "other": {"message": "nested error"}}
        msgs = extract_messages(data)
        self.assertIn("error here", msgs)
        self.assertIn("nested error", msgs)

    def test_extract_messages_list(self):
        data = [{"message": "list error 1"}, {"message": "list error 2"}]
        msgs = extract_messages(data)
        self.assertEqual(len(msgs), 2)

if __name__ == '__main__':
    unittest.main()
