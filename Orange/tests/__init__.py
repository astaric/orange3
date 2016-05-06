import os
import unittest
from contextlib import contextmanager

try:
    from Orange import widgets
    run_widget_tests = True
except ImportError:
    run_widget_tests = False


@contextmanager
def named_file(content, encoding=None):
    import tempfile
    import os
    file = tempfile.NamedTemporaryFile("wt", delete=False, encoding=encoding)
    file.write(content)
    name = file.name
    file.close()
    try:
        yield name
    finally:
        os.remove(name)


def suite(loader=None, pattern='test*.py'):
    test_dir = os.path.dirname(__file__)
    if loader is None:
        loader = unittest.TestLoader()
    if pattern is None:
        pattern = 'test*.py'
    all_tests = [
        #loader.discover(test_dir, pattern),
    ]

    if run_widget_tests:
        widgets_test_dir = os.path.dirname(widgets.__file__)
        loader = unittest.TestLoader()

        if hasattr(loader, '_find_test_path'):
            old_find_test_path = loader._find_test_path
            def _find_test_path(full_path, pattern, namespace=False):
                result = old_find_test_path(full_path, pattern, namespace)
                print(full_path, result)
                return result
            loader._find_test_path = _find_test_path
        else:
            old_loadTestsFromModule = loader.loadTestsFromModule
            def loadTestsFromModule(module, use_load_tests=True):
                result = old_loadTestsFromModule(module, use_load_tests)
                print(module, use_load_tests, result)
                return result
            loader.loadTestsFromModule = loadTestsFromModule

            old_match_path = loader._match_path
            def _match_path(path, full_path, pattern):
                result = old_match_path(full_path, pattern)
                print(full_path, pattern, result)
                return result
            loader._match_path = _match_path


        all_tests.extend([
            loader.discover(widgets_test_dir, pattern)
        ])
    return unittest.TestSuite(all_tests)


test_suite = suite()


def load_tests(loader, tests, pattern):
    return suite(loader, pattern)


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
