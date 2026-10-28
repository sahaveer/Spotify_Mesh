import pathlib
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import downloader
import config

class DownloaderTests(unittest.TestCase):
    def setUp(self):
        with downloader._lock:
            downloader._download_tasks.clear()

    def test_audio_video_and_both_destinations(self):
        with tempfile.TemporaryDirectory(dir=config.DATA_DIR) as directory:
            root=pathlib.Path(directory)
            for media_format in ('audio','video'):
                for destination in ('client','server'):
                    task_id=media_format+'_'+destination
                    task={'id':task_id,'title':'Fetching metadata...','status':'pending','target_dir':str(root)}
                    downloader._download_tasks[task_id]=task
                    extension='mp3' if media_format=='audio' else 'mp4'
                    output=root/(task_id+'_Demo.'+extension)
                    options=[]
                    class FakeYDL:
                        def __init__(self, opts): options.append(opts)
                        def __enter__(self): return self
                        def __exit__(self,*args): pass
                        def prepare_filename(self, entry): return str(output)
                        def extract_info(self, url, download):
                            output.write_bytes(b'x'*2048)
                            options[-1]['progress_hooks'][0]({'status':'downloading','downloaded_bytes':1024,'total_bytes':2048,'info_dict':{'title':'Demo'}})
                            return {'title':'Demo','duration':1}
                    with patch('downloader.yt_dlp.YoutubeDL',FakeYDL), patch('downloader.scanner.parse_media_file',return_value={'id':'indexed','title':'Demo'}), patch('database.upsert_song') as upsert, patch('downloader.threading.Thread'):
                        downloader._perform_download(task_id,'https://example.com/media',media_format,'720p',root,destination)
                    self.assertEqual(task['status'],'completed')
                    self.assertEqual(downloader.get_download_file(task_id),output.resolve())
                    self.assertEqual(options[0]['socket_timeout'],20)
                    self.assertTrue(options[0]['noplaylist'])
                    self.assertEqual(upsert.call_count,1 if destination=='server' else 0)
                    self.assertIn('/api/downloads/' if destination=='client' else '/api/stream/',task['download_url'])

    def test_no_file_cannot_be_completed_or_return_unrelated_media(self):
        with tempfile.TemporaryDirectory(dir=config.DATA_DIR) as directory:
            root=pathlib.Path(directory)
            (root/'existing.mp4').write_bytes(b'x'*2048)
            downloader._download_tasks['missing']={'id':'missing','title':'Fetching metadata...','status':'pending','target_dir':str(root)}
            fake=MagicMock()
            fake.__enter__.return_value=fake
            fake.extract_info.return_value={'title':'Not downloaded'}
            fake.prepare_filename.return_value=str(root/'missing.mp4')
            with patch('downloader.yt_dlp.YoutubeDL',return_value=fake):
                downloader._perform_download('missing','https://example.com/file','video','best',root)
            self.assertEqual(downloader.get_download_status('missing')['status'],'failed')
            self.assertIsNone(downloader.get_download_file('missing'))

    def test_worker_reports_folder_creation_failure(self):
        with tempfile.TemporaryDirectory(dir=config.DATA_DIR) as directory:
            obstacle=pathlib.Path(directory)/'file'
            obstacle.write_text('not a directory')
            downloader._download_tasks['blocked']={'id':'blocked','url':'https://example.com/media','format':'audio','quality':'best','target_dir':str(obstacle/'child'),'destination':'client','owner_id':'test','owner_name':'Test','title':'Fetching metadata...','status':'pending'}
            downloader._run_download('blocked','https://example.com/media','audio','best',obstacle/'child','client')
            task=downloader.get_download_status('blocked')
            self.assertEqual(task['status'],'failed')
            self.assertTrue(task['error'])

    def test_browser_cookies_configured_in_ydl_opts(self):
        with tempfile.TemporaryDirectory(dir=config.DATA_DIR) as directory:
            root = pathlib.Path(directory)
            task_id = "test_cookies"
            task = {'id': task_id, 'title': 'Fetching metadata...', 'status': 'pending', 'target_dir': str(root)}
            downloader._download_tasks[task_id] = task
            output = root / (task_id + '_Demo.mp4')
            options = []

            class FakeYDL:
                def __init__(self, opts): options.append(opts)
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def prepare_filename(self, entry): return str(output)
                def extract_info(self, url, download):
                    output.write_bytes(b'x'*1024)
                    return {'title': 'Demo Instagram Reel', 'duration': 15}

            with patch('downloader.yt_dlp.YoutubeDL', FakeYDL), patch('downloader.scanner.parse_media_file', return_value={'id': 'ig_reel', 'title': 'Demo Reel'}), patch('database.upsert_song'), patch('downloader.threading.Thread'):
                downloader._perform_download(task_id, 'https://www.instagram.com/reel/C3xyz99/', 'video', 'best', root, 'server', cookies_browser='chrome')

            self.assertEqual(task['status'], 'completed')
            self.assertEqual(options[0].get('cookiesfrombrowser'), ('chrome',))

    def test_start_download_respects_cookies_browser_override(self):
        with patch('downloader.threading.Thread') as mock_thread:
            task_id = downloader.start_download(
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                media_format="video",
                quality="1080p",
                destination="server",
                cookies_browser="firefox"
            )
            task = downloader.get_download_status(task_id)
            self.assertEqual(task["cookies_browser"], "firefox")
            mock_thread.assert_called_once()
            args = mock_thread.call_args[1]["args"]
            self.assertEqual(args[-1], "firefox")  # cookies_browser is the last argument

    def test_missing_youtube_support_is_actionable(self):
        with patch('downloader.importlib.util.find_spec',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'yt-dlp'):
                downloader._youtube_runtime()

    def test_stalled_metadata_worker_is_stopped(self):
        downloader._download_tasks['stalled']={'id':'stalled','title':'Fetching metadata...','status':'pending'}
        process=MagicMock()
        process.poll.return_value=None
        process.stdout=[]
        with patch('downloader.subprocess.Popen',return_value=process), patch('downloader.subprocess.run'), patch('downloader.os.killpg',create=True), patch('downloader.time.monotonic',side_effect=[0,121]), patch('downloader.threading.Thread'):
            downloader._run_download('stalled','https://example.com/file','audio','best',pathlib.Path('.'),'client')
        self.assertEqual(downloader.get_download_status('stalled')['status'],'failed')
        self.assertIn('timed out',downloader.get_download_status('stalled')['error'])
        process.wait.assert_called_once()

if __name__=='__main__': unittest.main()
