import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules import ollama_manager as om


def _msgs(chars):
    return [{'role': 'system', 'content': 'x' * chars}]


class TestContextSize(unittest.TestCase):
    def test_short_conversation_gets_minimum(self):
        self.assertEqual(om.context_size(_msgs(1000)), om.MIN_CONTEXT)

    def test_transcript_fits_with_room_for_answer(self):
        # ~44 000 chars: the 7 400-word Yann LeCun transcript (10 456 real tokens)
        size = om.context_size(_msgs(44000))
        self.assertEqual(size, 16384)
        self.assertGreaterEqual(size, 10456 + om.ANSWER_TOKENS)

    def test_one_hour_video(self):
        # ~67 000 chars, ~12 000 words
        self.assertEqual(om.context_size(_msgs(67000)), 24576)

    def test_capped_by_model_maximum(self):
        self.assertEqual(om.context_size(_msgs(500000), max_context=32768), 32768)

    def test_grows_with_history(self):
        msgs = _msgs(44000) + [{'role': 'assistant', 'content': 'y' * 20000}]
        self.assertGreater(om.context_size(msgs), om.context_size(_msgs(44000)))


class TestChatUsesContext(unittest.TestCase):
    def test_chat_passes_num_ctx_and_whole_transcript(self):
        with patch.object(om, 'Client') as client_cls:
            client = client_cls.return_value
            client.show.return_value = MagicMock(modelinfo={'qwen35.context_length': 262144},
                                                 capabilities=['completion', 'thinking'])
            client.chat.side_effect = lambda **kw: iter([{'message': {'content': 'o'}}, {'message': {'content': 'k'}}])
            manager = om.OllamaManager(model='qwen3.5:4b')
            transcript = os.path.join(os.path.dirname(__file__), 'test_chat.txt')
            with open(transcript, encoding='utf-8') as f:
                text = f.read()
            with patch('builtins.input', side_effect=['Résume', 'exit']), \
                 patch('builtins.print'):
                manager.interactive_chat(transcript)
            kwargs = client.chat.call_args.kwargs
            self.assertIn(text, kwargs['messages'][0]['content'])
            # messages is the live history: the call saw it before the answer was appended
            self.assertEqual(kwargs['options']['num_ctx'], om.context_size(kwargs['messages'][:3], 262144))
            self.assertGreaterEqual(kwargs['options']['num_ctx'], om.MIN_CONTEXT)
            self.assertIs(kwargs['think'], False)
            self.assertIs(kwargs['stream'], True)
            # the streamed parts are joined into the history
            self.assertEqual(kwargs['messages'][-1], {'role': 'assistant', 'content': 'ok'})

    def test_ctrl_c_stops_the_answer_but_not_the_chat(self):
        def interrupted(**kw):
            yield {'message': {'content': 'par'}}
            raise KeyboardInterrupt
        with patch.object(om, 'Client') as client_cls:
            client = client_cls.return_value
            client.show.return_value = MagicMock(modelinfo={}, capabilities=[])
            answers = [interrupted, lambda **kw: iter([{'message': {'content': 'done'}}])]
            client.chat.side_effect = lambda **kw: answers.pop(0)(**kw)
            manager = om.OllamaManager(model='m')
            transcript = os.path.join(os.path.dirname(__file__), 'test_chat.txt')
            with patch('builtins.input', side_effect=['q1', 'q2', 'exit']), patch('builtins.print'):
                manager.interactive_chat(transcript)
            history = client.chat.call_args.kwargs['messages']
            # q1 and its partial answer were dropped, q2 was answered
            self.assertEqual([m['content'] for m in history[2:]], ['q2', 'done'])

    def test_non_thinking_model_gets_no_think_argument(self):
        with patch.object(om, 'Client') as client_cls:
            client = client_cls.return_value
            client.show.return_value = MagicMock(modelinfo={}, capabilities=['completion'])
            client.chat.side_effect = lambda **kw: iter([{'message': {'content': 'o'}}, {'message': {'content': 'k'}}])
            manager = om.OllamaManager(model='llama3.2')
            transcript = os.path.join(os.path.dirname(__file__), 'test_chat.txt')
            with patch('builtins.input', side_effect=['hi', 'exit']), patch('builtins.print'):
                manager.interactive_chat(transcript)
            self.assertNotIn('think', client.chat.call_args.kwargs)


class TestAnswerDetails(unittest.TestCase):
    def test_verbose_shows_tokens_speed_and_gpu_share(self):
        with patch.object(om, 'Client') as client_cls:
            client = client_cls.return_value
            client.ps.return_value = MagicMock(models=[MagicMock(model='qwen3.5:4b', size=3.6e9, size_vram=3.6e9)])
            manager = om.OllamaManager(model='qwen3.5:4b')
            last = {'message': {'content': ''}, 'done': True, 'prompt_eval_count': 10435,
                    'eval_count': 400, 'eval_duration': 8e9, 'load_duration': 1e8}
            with patch.object(om.ui, 'verbose', True), patch.dict(os.environ, {'NO_COLOR': '1'}), \
                 patch('builtins.print') as printed:
                manager._answer_details(last, 16384)
        lines = [c.args[0] for c in printed.call_args_list]
        self.assertEqual(lines, ['    · Read 10435 new tokens, wrote 400 tokens at 50.0 tokens/s',
                                 '    · Model loaded: 3.6 GB with a 16384-token context, 3.6 GB on the GPU (100%)'])


if __name__ == '__main__':
    unittest.main()
