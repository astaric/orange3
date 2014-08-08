from io import StringIO
from unittest import TestCase
from Orange.data.sql.table import SqlTable
from Orange.data.sql.reader import SqlReader


class TestSqlReader(TestCase):
    def setUp(self):
        self.reader = SqlReader()

    def test_uri_connection(self):
        connection_params, type_hints = self.reader._parse_header(
            """% CONNECTION
% uri:      sql://localhost/test/iris
% DOMAIN
% test: d""")
        self.assertEqual(1, len(connection_params))
        self.assertIn('uri', connection_params)
        self.assertEqual('sql://localhost/test/iris', connection_params['uri'])




def create_file(content):
    file = StringIO()
    file.write(content)
    file.seek(0)
    return file
