import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from fastapi import HTTPException
import config
import streamer
import imageio_ffmpeg

class StreamingTests(unittest.TestCase):
    def test_background_preparation_status_and_retry(self):
        with tempfile.TemporaryDirectory(dir=config.DATA_DIR) as directory:
            source = pathlib.Path(directory) / 'video.mp4'
            source.write_bytes(b'test')
            pending = []
            class DeferredThread:
                def __init__(self, target, **kwargs):
                    pending.append(target)
                def start(self):
                    pass
            with patch('streamer.threading.Thread', DeferredThread), patch('streamer.compatible_media') as convert:
                self.assertEqual(streamer.compatibility_job(str(source), True)['status'], 'idle')
                self.assertEqual(streamer.compatibility_job(str(source), True, start=True)['status'], 'preparing')
                streamer.compatibility_job(str(source), True, start=True)
                self.assertEqual(len(pending), 1)
                convert.side_effect = HTTPException(status_code=422, detail='Damaged file')
                pending.pop()()
                self.assertEqual(streamer.compatibility_job(str(source), True)['detail'], 'Damaged file')
                streamer.compatibility_job(str(source), True, start=True)
                convert.side_effect = None
                pending.pop()()
                self.assertEqual(streamer.compatibility_job(str(source), True)['status'], 'ready')
                source.write_bytes(b'changed file')
                self.assertEqual(streamer.compatibility_job(str(source), True)['status'], 'idle')

    def test_range_requests(self):
        for header, expected in [('bytes=0-99',(0,99,100)),('bytes=100-9999',(100,999,900)),('bytes=-100',(900,999,100)),('bytes=-9999',(0,999,1000)),('bytes=999-',(999,999,1))]:
            self.assertEqual(streamer.parse_range_header(header,1000),expected)
        for header in ('bytes=1000-','bytes=20-10','bytes=-0','bytes=-'):
            with self.assertRaises(HTTPException) as error: streamer.parse_range_header(header,1000)
            self.assertEqual(error.exception.status_code,416)

    def test_real_compatible_video_and_audio(self):
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
        with tempfile.TemporaryDirectory(dir=config.DATA_DIR) as directory:
            root=pathlib.Path(directory)
            video=root/'old.mp4'
            audio=root/'audio.wav'
            subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','color=size=64x64:rate=10','-f','lavfi','-i','sine=frequency=440','-t','1','-c:v','mpeg4','-c:a','aac',str(video)],check=True)
            subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','sine=frequency=440','-t','1',str(audio)],check=True)
            with patch.object(config,'CACHE_DIR',root/'cache'):
                for source,is_video in ((video,True),(audio,False)):
                    response=streamer.compatible_media(str(source),is_video)
                    target=pathlib.Path(response.path)
                    self.assertTrue(target.is_file())
                    self.assertGreater(target.stat().st_size,0)
                    result=subprocess.run([ffmpeg,'-hide_banner','-i',str(target)],capture_output=True,text=True)
                    self.assertIn('Video: h264' if is_video else 'Audio: mp3',result.stderr)
                    with patch('streamer.subprocess.run',side_effect=AssertionError('Cache should be reused')):
                        self.assertEqual(streamer.compatible_media(str(source),is_video).path,response.path)
                    self.assertTrue(source.is_file())
                corrupt=root/'broken.mp4'
                corrupt.write_bytes(b'not a video')
                with self.assertRaises(HTTPException) as error: streamer.compatible_media(str(corrupt),True)
                self.assertEqual(error.exception.status_code,422)
                self.assertFalse(list((root/'cache'/'playback').glob('tmp*')))

if __name__=='__main__': unittest.main()
