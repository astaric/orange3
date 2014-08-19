from io import StringIO
from unittest import TestCase
from mock import patch, Mock, MagicMock
from Orange.data import DiscreteVariable, ContinuousVariable
from Orange.data.sql.table import SqlTable
from Orange.data.sql.reader import SqlReader


class TestSqlReader(TestCase):
    def setUp(self):
        self.reader = SqlReader()

    def test_only_connection_parameters(self):
        connection_params, type_hints = self.reader._parse_header(
            """% CONNECTION
% uri:      sql://localhost/test/iris""")
        self.assertEqual(1, len(connection_params))
        self.assertEqual(0, len(type_hints))
        self.assertIn('uri', connection_params)
        self.assertEqual('sql://localhost/test/iris', connection_params['uri'])

    def test_only_domain_hints(self):
        connection_params, type_hints = self.reader._parse_header(
            """% DOMAIN
% attr1:  discrete
% attr2:  continuous""")
        self.assertEqual(0, len(connection_params))
        self.assertEqual(2, len(type_hints))
        self.assertIn('attr1', type_hints)
        self.assertIn('attr2', type_hints)
        self.assertEqual('discrete', type_hints['attr1'])
        self.assertEqual('continuous', type_hints['attr2'])

    def test_connection_parameters_and_domain_hints(self):
        connection_params, type_hints = self.reader._parse_header(
            """% CONNECTION
% host:      host
% database:  database
% user:      user
% password:  password
% schema:    schema
% DOMAIN
% attr1:  discrete
% attr2:  continuous""")
        self.assertEqual(5, len(connection_params))
        self.assertEqual(2, len(type_hints))
        self.assertIn('host', connection_params)
        self.assertIn('database', connection_params)
        self.assertIn('user', connection_params)
        self.assertIn('password', connection_params)
        self.assertIn('schema', connection_params)
        self.assertEqual('host', connection_params['host'])
        self.assertEqual('database', connection_params['database'])
        self.assertEqual('user', connection_params['user'])
        self.assertEqual('password', connection_params['password'])
        self.assertEqual('schema', connection_params['schema'])
        self.assertIn('attr1', type_hints)
        self.assertIn('attr2', type_hints)
        self.assertEqual('discrete', type_hints['attr1'])
        self.assertEqual('continuous', type_hints['attr2'])

    def test_parse_domain_hints_parses_discrete_type(self):
        type_hints = self.reader._parse_domain_params({
            'attr1': 'd',
            'attr2': 'DISCRETE',
        })
        self.assertEqual(2, len(type_hints))
        self.assertIn('attr1', type_hints)
        self.assertIn('attr2', type_hints)
        self.assertIsInstance(type_hints['attr1'], DiscreteVariable)
        self.assertIsInstance(type_hints['attr2'], DiscreteVariable)
        self.assertEqual('attr1', type_hints['attr1'].name)
        self.assertEqual('attr2', type_hints['attr2'].name)

    def test_parse_domain_hints_parses_values(self):
        type_hints = self.reader._parse_domain_params({
            'attr1': '{a,b,c}',
            'attr2': '{sepal length,sepal width,petal length}',
        })
        self.assertEqual(2, len(type_hints))
        self.assertIn('attr1', type_hints)
        self.assertIn('attr2', type_hints)
        self.assertIsInstance(type_hints['attr1'], DiscreteVariable)
        self.assertIsInstance(type_hints['attr2'], DiscreteVariable)
        self.assertEqual('attr1', type_hints['attr1'].name)
        self.assertEqual('attr2', type_hints['attr2'].name)
        self.assertSequenceEqual(['a', 'b', 'c'], type_hints['attr1'].values)
        self.assertSequenceEqual(
            ['sepal length', 'sepal width', 'petal length'],
            type_hints['attr2'].values)

    def test_parse_domain_hints_parses_continuous_type(self):
        type_hints = self.reader._parse_domain_params({
            'attr1': 'C',
            'attr2': 'continuous',
        })
        self.assertEqual(2, len(type_hints))
        self.assertIn('attr1', type_hints)
        self.assertIn('attr2', type_hints)
        self.assertIsInstance(type_hints['attr1'], ContinuousVariable)
        self.assertIsInstance(type_hints['attr2'], ContinuousVariable)
        self.assertEqual('attr1', type_hints['attr1'].name)
        self.assertEqual('attr2', type_hints['attr2'].name)

    def test_parse_class_vars(self):
        type_hints = self.reader._parse_domain_params({
            'attr1': 'C class',
            'attr2': 'discrete meta',
        })
        self.assertEqual(4, len(type_hints))
        self.assertIn('attr1', type_hints)
        self.assertIn('attr2', type_hints)
        self.assertIn('__classvars__', type_hints)
        self.assertIn('__metas__', type_hints)
        self.assertIsInstance(type_hints['attr1'], ContinuousVariable)
        self.assertIsInstance(type_hints['attr2'], DiscreteVariable)
        self.assertEqual('attr1', type_hints['attr1'].name)
        self.assertEqual('attr2', type_hints['attr2'].name)
        self.assertIn('attr1', type_hints['__classvars__'])
        self.assertIn('attr2', type_hints['__metas__'])

    def test_read_file(self):
        expected_table = object()
        MockSqlTable = MagicMock()
        MockSqlTable.return_value = expected_table
        table = self.reader._read_file(create_file("""
% CONNECTION
% host:      host
% database:  database
% user:      user
% password:  password
% schema:    schema
% DOMAIN
% attr1:  continuous
% attr2:  discrete class
SELECT attr1, attr2 FROM table
        """), cls=MockSqlTable)

        self.assertTrue(MockSqlTable.called)
        args, kwargs = MockSqlTable.call_args
        self.assertIn('host', kwargs)
        self.assertIn('database', kwargs)
        self.assertIn('user', kwargs)
        self.assertIn('password', kwargs)
        self.assertIn('schema', kwargs)
        self.assertIn('type_hints', kwargs)
        self.assertIn('__classvars__', kwargs['type_hints'])
        self.assertIs(expected_table, table)


def create_file(content):
    file = StringIO()
    file.write(content)
    file.seek(0)
    return file
