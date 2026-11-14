import glob
import json
import os
import tempfile
import unittest

from modules.source_export import (SCHEMA, file_source, source_path, validate_source,
                                   write_source, youtube_source)

INFO = {'id': 'JfoqQJbz8VA', 'title': "Néandertal I et l'Homme de la Chapelle-aux-Saints : quels points communs ?",
        'channel': "Musée de l'Homme", 'uploader': 'museedelhomme', 'upload_date': '20240502'}
SEGMENTS = [(0.0, 4.24, " La découverte de Néandertal 1 "), (4.24, 9.5, "n'était pas reconnue « tout de suite ».")]
SETTINGS = {'engine': 'faster-whisper', 'model': 'large-v3-turbo', 'device': 'cuda',
            'compute_type': 'float16', 'batch_size': 16, 'language': 'fr', 'language_source': 'youtube'}
PLAYLIST_A = {'id': 'PLaaa', 'title': 'Préhistoire'}
PLAYLIST_B = {'id': 'PLbbb', 'title': 'Néandertal'}


class TestYoutubeSource(unittest.TestCase):
    def test_contract(self):
        source = youtube_source(INFO, SEGMENTS, SETTINGS, playlist=PLAYLIST_A, position=4)
        validate_source(source)
        self.assertEqual(source['schema'], SCHEMA)
        self.assertEqual(source['source_id'], 'youtube:JfoqQJbz8VA')  # from the id, not the title
        self.assertEqual(source['youtube']['url'], 'https://www.youtube.com/watch?v=JfoqQJbz8VA')
        self.assertEqual(source['channel'], "Musée de l'Homme")
        self.assertNotIn('author', source)  # the channel is not the speaker nor the scientist
        self.assertEqual(source['published'], '2024-05-02')
        self.assertEqual(source['language'], 'fr')
        self.assertEqual(source['playlists'], [{'id': 'PLaaa', 'title': 'Préhistoire', 'position': 4}])
        self.assertEqual(source['segments'][1], {'id': 's0002', 'start': 4.24, 'end': 9.5,
                                                 'text': "n'était pas reconnue « tout de suite »."})

    def test_same_transcription_same_version(self):
        a = youtube_source(INFO, SEGMENTS, SETTINGS)
        b = youtube_source(INFO, SEGMENTS, SETTINGS, playlist=PLAYLIST_B, position=1)
        self.assertEqual(a['text_version'], b['text_version'])  # playlists are not the text

    def test_other_model_is_another_version(self):
        other = dict(SETTINGS, model='base', device='cpu')
        self.assertNotEqual(youtube_source(INFO, SEGMENTS, SETTINGS)['text_version'],
                            youtube_source(INFO, SEGMENTS, other)['text_version'])

    def test_invalid_segments_are_refused(self):
        for segments in ([(5.0, 4.0, 'x')], [(3.0, 4.0, 'a'), (1.0, 2.0, 'b')]):
            with self.assertRaises(ValueError):
                validate_source(youtube_source(INFO, segments, SETTINGS))


class TestWriteSource(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.work = self.dir.name

    def tearDown(self):
        self.dir.cleanup()

    def _files(self):
        return glob.glob(os.path.join(self.work, 'sources', '**', '*.json'), recursive=True)

    def test_utf8_file_readable_by_anyone(self):
        path = write_source(self.work, youtube_source(INFO, SEGMENTS, SETTINGS))
        with open(path, encoding='utf-8') as f:
            raw = f.read()
        self.assertIn('Néandertal', raw)  # written as text, not \\u escapes
        self.assertTrue(path.endswith('.json') and 'JfoqQJbz8VA' in path)
        self.assertEqual(json.loads(raw)['segments'][0]['text'], 'La découverte de Néandertal 1')

    def test_readable_names(self):
        source = youtube_source({'id': '9ePdrj096XY', 'title': 'Le SECRET le MIEUX GARDÉ de nos ÉLITES'},
                                SEGMENTS, SETTINGS)
        path = write_source(self.work, source)
        folder, name = os.path.split(os.path.relpath(path, self.work))
        self.assertEqual(folder, os.path.join('sources', 'youtube', 'Le_SECRET_le_MIEUX_GARDE_de_nos_ELITES_9ePdrj096XY'))
        version = source['text_version'].replace('sha256:', '')[:6]
        self.assertEqual(name, f"{source['collected_at'][:10]}_large-v3-turbo_{version}.json")

    def test_renamed_video_keeps_its_folder(self):
        first = write_source(self.work, youtube_source(INFO, SEGMENTS, SETTINGS))
        renamed = dict(INFO, title='Un tout autre titre')
        second = write_source(self.work, youtube_source(renamed, SEGMENTS, dict(SETTINGS, model='base')))
        self.assertEqual(os.path.dirname(first), os.path.dirname(second))

    def test_same_transcription_another_day_is_the_same_file(self):
        path = write_source(self.work, youtube_source(INFO, SEGMENTS, SETTINGS))
        later = dict(youtube_source(INFO, SEGMENTS, SETTINGS), collected_at='2030-01-01T00:00:00Z')
        self.assertEqual(write_source(self.work, later), path)
        self.assertEqual(len(self._files()), 1)

    def test_writing_again_changes_nothing(self):
        path = write_source(self.work, youtube_source(INFO, SEGMENTS, SETTINGS))
        before = os.stat(path).st_mtime_ns
        self.assertEqual(write_source(self.work, youtube_source(INFO, SEGMENTS, SETTINGS)), path)
        self.assertEqual(os.stat(path).st_mtime_ns, before)
        self.assertEqual(len(self._files()), 1)

    def test_video_in_two_playlists_stays_one_source(self):
        write_source(self.work, youtube_source(INFO, SEGMENTS, SETTINGS, playlist=PLAYLIST_A, position=4))
        write_source(self.work, youtube_source(INFO, SEGMENTS, SETTINGS, playlist=PLAYLIST_B, position=1))
        path = write_source(self.work, youtube_source(INFO, SEGMENTS, SETTINGS, playlist=PLAYLIST_A, position=4))
        self.assertEqual(len(self._files()), 1)
        with open(path, encoding='utf-8') as f:
            self.assertEqual([p['id'] for p in json.load(f)['playlists']], ['PLaaa', 'PLbbb'])

    def test_new_transcription_is_a_new_version(self):
        first = write_source(self.work, youtube_source(INFO, SEGMENTS, SETTINGS))
        second = write_source(self.work, youtube_source(INFO, SEGMENTS, dict(SETTINGS, model='base')))
        self.assertNotEqual(first, second)
        self.assertEqual(os.path.dirname(first), os.path.dirname(second))  # same video folder
        self.assertEqual(len(self._files()), 2)

    def test_local_file_identified_by_content(self):
        mp3 = os.path.join(self.work, 'a.mp3')
        with open(mp3, 'wb') as f:
            f.write(b'ID3 fake audio')
        source = file_source(mp3, {'title': 'Cours 1'}, SEGMENTS, SETTINGS)
        renamed = os.path.join(self.work, 'renamed.mp3')
        os.rename(mp3, renamed)
        same = file_source(renamed, {'title': 'Cours 1'}, SEGMENTS, SETTINGS)
        self.assertEqual(source['source_id'], same['source_id'])
        self.assertTrue(source['source_id'].startswith('file:sha256:'))
        self.assertIn(os.path.join('sources', 'files'), source_path(self.work, source))


if __name__ == '__main__':
    unittest.main()
