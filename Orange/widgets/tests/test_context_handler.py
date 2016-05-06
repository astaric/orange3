from unittest import TestCase
from unittest.mock import Mock
from Orange.widgets.settings import ContextHandler, Setting, ContextSetting

print("TEST CONTEXT HANDLER!!!")


class SimpleWidget:
    setting = Setting(42)

    context_setting = ContextSetting(42)


class ContextHandlerTestCase(TestCase):
    def setUp(self):
        print("Pa sej nekej delam!!!")
    def test_initialize(self):
        handler = ContextHandler()
        handler.provider = Mock()

        # Context settings from data
        widget = SimpleWidget()
        handler.initialize(widget, {'context_settings': 5})
        self.assertTrue(hasattr(widget, 'context_settings'))
        self.assertEqual(widget.context_settings, 5)

        # Default (global) context settings
        widget = SimpleWidget()
        handler.initialize(widget)
        self.assertTrue(hasattr(widget, 'context_settings'))
        self.assertEqual(widget.context_settings, handler.global_contexts)

    def test_fast_save(self):
        handler = ContextHandler()
        handler.bind(SimpleWidget)

        widget = SimpleWidget()
        handler.initialize(widget)

        context = widget.current_context = handler.new_context()
        handler.fast_save(widget, 'context_setting', 55)
        self.assertEqual(context.values['context_setting'], 55)
