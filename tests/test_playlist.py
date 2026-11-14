import glob
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import yt2post
from modules import ui
from modules.clipboard import find_youtube_url
from modules.transcriber import safe_file_name, whisper_language
from modules.youtube_downloader import has_video, playlist_id

IN_PLAYLIST = 'https://www.youtube.com/watch?v=JfoqQJbz8VA&list=PLEnK6o7pdzkdtZJ1FmPqXO6VRu-09pEGv'
PLAYLIST = 'https://www.youtube.com/playlist?list=PLEnK6o7pdzkdtZJ1FmPqXO6VRu-09pEGv'


def _playlist(n=3):
    return {'title': 'Préhistoire', 'uploader': "Musée de l'Homme", 'url': PLAYLIST, 'id': 'PLtest',
            'entries': [{'title': f'Video {i}', 'url': f'https://youtu.be/v{i}', 'duration': 60}
                        for i in range(1, n + 1)]}


class TestLinks(unittest.TestCase):
    def test_playlist_id(self):
        self.assertEqual(playlist_id(IN_PLAYLIST), 'PLEnK6o7pdzkdtZJ1FmPqXO6VRu-09pEGv')
        self.assertEqual(playlist_id(PLAYLIST), 'PLEnK6o7pdzkdtZJ1FmPqXO6VRu-09pEGv')
        self.assertIsNone(playlist_id('https://youtu.be/JfoqQJbz8VA?si=x'))

    def test_has_video(self):
        self.assertTrue(has_video(IN_PLAYLIST))
        self.assertTrue(has_video('https://youtu.be/JfoqQJbz8VA?list=PL1'))
        self.assertFalse(has_video(PLAYLIST))

    def test_playlist_link_found_in_clipboard(self):
        self.assertEqual(find_youtube_url(f'see {PLAYLIST} now'), PLAYLIST)

    def test_whisper_language_from_youtube_code(self):
        self.assertEqual([whisper_language(c) for c in ('fr-FR', 'en', 'pt_BR', None, 'xx-YY')],
                         ['fr', 'en', 'pt', None, None])


class TestChoosePlaylistMode(unittest.TestCase):
    def _choose(self, url, answers, mode=None, chat=False):
        with patch('builtins.input', side_effect=answers), patch('builtins.print') as printed:
            result = yt2post.choose_playlist_mode(url, _playlist(), mode, chat)
        return result, ' '.join(str(c.args[0]) for c in printed.call_args_list if c.args)

    def test_summary_is_shown(self):
        _, out = self._choose(IN_PLAYLIST, ['1'])
        self.assertIn("Préhistoire by Musée de l'Homme: 3 videos, 3:00 of audio", out)

    def test_video_only_by_default(self):
        self.assertEqual(self._choose(IN_PLAYLIST, [''])[0], 'video')

    def test_whole_playlist_one_file_per_video(self):
        self.assertEqual(self._choose(IN_PLAYLIST, ['2', ''])[0], 'separate')

    def test_whole_playlist_one_file(self):
        self.assertEqual(self._choose(IN_PLAYLIST, ['2', '2'])[0], 'combined')

    def test_playlist_link_asks_only_the_file_question(self):
        self.assertEqual(self._choose(PLAYLIST, ['2'])[0], 'combined')

    def test_chat_defaults_to_one_file(self):
        self.assertEqual(self._choose(PLAYLIST, [''], chat=True)[0], 'combined')

    def test_no_terminal_takes_the_defaults(self):
        self.assertEqual(self._choose(IN_PLAYLIST, EOFError)[0], 'video')
        self.assertEqual(self._choose(PLAYLIST, EOFError)[0], 'separate')

    def test_option_answers_without_asking(self):
        self.assertEqual(self._choose(IN_PLAYLIST, [], mode='combined')[0], 'combined')

    def test_video_option_needs_a_video(self):
        with self.assertRaisesRegex(Exception, 'use -p separate or -p combined'):
            self._choose(PLAYLIST, [], mode='video')


class TestTranscribePlaylist(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.work = os.path.join(self.dir.name, 'work')
        self.tmp = os.path.join(self.dir.name, 'tmp')
        os.makedirs(self.work)
        os.makedirs(self.tmp)

    def tearDown(self):
        self.dir.cleanup()

    def _transcripts(self):
        return sorted(f for f in os.listdir(self.work) if f.endswith('.txt'))

    def _run(self, mode, fail=(), chat=False):
        downloader = MagicMock()
        audio = {}

        def download(url):
            if url in fail:
                raise Exception('Video unavailable')
            path = os.path.join(self.tmp, url[-2:] + '.webm')
            open(path, 'w').close()
            audio[url] = path
            downloader.info = {'id': 'vid' + url[-2:], 'title': 'Real ' + url[-2:],
                               'channel': "Musée de l'Homme", 'upload_date': '20240502'}
            return path, path + '.json'

        downloader.download_audio.side_effect = download
        downloader.downloaded_size.return_value = '1.0 MB'
        transcriber = MagicMock(audio_duration=60, language='fr', language_given=True,
                                model_name='base', device='cpu', compute_type='int8',
                                BATCH_SIZE=16, segments=[(0.0, 4.2, ' Bonjour à tous.')])
        transcriber.transcript.side_effect = lambda a, j, url: (f'Title {url[-2:]}', f'Text of {url[-2:]}')
        steps = ui.Steps(['Loading'] + [f'Video {i}' for i in range(1, 4)])
        steps.next()
        out = io.StringIO()
        with patch.object(sys, 'stdout', out), patch.object(yt2post, 'write_clipboard', return_value=True):
            result = yt2post.transcribe_playlist(steps, transcriber, downloader, _playlist(), mode,
                                                 self.work, self.tmp, chat)
        self.assertFalse(any(os.path.exists(p) for p in audio.values()))  # audio freed as it goes
        return result, out.getvalue()

    def test_one_file_per_video_numbered(self):
        result, out = self._run('separate')
        self.assertIsNone(result)
        self.assertEqual(self._transcripts(),
                         ['1_Title_v1_transcript.txt', '2_Title_v2_transcript.txt', '3_Title_v3_transcript.txt'])
        self.assertIn('Transcripts saved to:', out)
        self.assertIn('Directory path copied', out)
        self.assertIn('Real v2', out)  # the video's own title after its download
        # One timestamped source per video, with its place in the playlist
        sources = sorted(glob.glob(os.path.join(self.work, 'sources', 'youtube', '*', '*.json')))
        self.assertEqual(len(sources), 3)
        with open(sources[1], encoding='utf-8') as f:
            source = json.load(f)
        self.assertEqual(source['source_id'], 'youtube:vidv2')
        self.assertEqual(source['playlists'], [{'id': 'PLtest', 'title': 'Préhistoire', 'position': 2}])

    def test_one_file_with_everything(self):
        result, out = self._run('combined')
        self.assertEqual(self._transcripts(), [os.path.basename(result)])
        with open(result, encoding='utf-8') as f:
            text = f.read()
        self.assertIn('the 3 videos of the YouTube playlist "Préhistoire"', text)
        self.assertLess(text.index('=== Video 1/3 ===\n\nText of v1'), text.index('=== Video 3/3 ===\n\nText of v3'))
        self.assertIn('All the transcripts saved to:', out)

    def test_chat_with_separate_files_reads_a_combined_copy(self):
        result, _ = self._run('separate', chat=True)
        self.assertEqual(os.path.dirname(result), self.tmp)
        self.assertEqual(len(self._transcripts()), 3)

    def test_failed_video_is_skipped(self):
        _, out = self._run('separate', fail={'https://youtu.be/v2'})
        self.assertEqual(len(self._transcripts()), 2)
        self.assertIn('Skipped: Video unavailable', out)
        self.assertIn('1 of 3 videos could not be transcribed', out)

    def test_every_video_failing_is_an_error(self):
        with self.assertRaisesRegex(Exception, 'No video of the playlist could be transcribed'):
            self._run('combined', fail={f'https://youtu.be/v{i}' for i in range(1, 4)})


class TestHelpers(unittest.TestCase):
    def test_safe_file_name(self):
        self.assertEqual(safe_file_name('03_Néandertal : ../../etc'), '03_Néandertal_________etc')

    def test_choose_retries_until_valid(self):
        with patch('builtins.input', side_effect=['0', 'x', '2']), patch('builtins.print'):
            self.assertEqual(ui.choose(['a', 'b']), 1)

    def test_saved_files(self):
        out = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch.object(sys, 'stdout', out):
            ui.saved_files('Saved:', ['/w/1_a.txt', '/w/2_b.txt'])
        self.assertEqual(out.getvalue().splitlines()[2:],
                         ['  Dir:   /w/', '  Files: 1_a.txt', '         2_b.txt'])


if __name__ == '__main__':
    unittest.main()
