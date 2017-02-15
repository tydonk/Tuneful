import unittest
import os
import shutil
import json
try: from urllib.parse import urlparse
except ImportError: from urlparse import urlparse # Py2 compatibility
from io import StringIO, BytesIO

import sys; print(list(sys.modules.keys()))
# Configure our app to use the testing databse
os.environ["CONFIG_PATH"] = "tuneful.config.TestingConfig"

from tuneful import app
from tuneful import models
from tuneful.utils import upload_path
from tuneful.database import Base, engine, session

class TestAPI(unittest.TestCase):
    """ Tests for the tuneful API """

    def setUp(self):
        """ Test setup """
        self.client = app.test_client()

        # Set up the tables in the database
        Base.metadata.create_all(engine)

        # Create folder for test uploads
        os.mkdir(upload_path())

    def test_get_empty_songs(self):
        """ Getting songs from an empty database """
        response = self.client.get("/api/songs",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(data, [])

    def test_get_songs(self):
        """ Getting songs from a populated database """
        fileA = models.File(name="test1.mp3")
        fileB = models.File(name="test2.mp3")

        songA = models.Song(file=fileA)
        songB = models.Song(file=fileB)

        session.add_all([fileA, fileB, songA, songB])
        session.commit()

        response = self.client.get("/api/songs",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(len(data), 2)

        songA = data[0]
        self.assertEqual(songA['id'], 1)
        self.assertEqual(songA['file'], {'name': 'test1.mp3',
                                         'id': 1,
                                         'path': '/uploads/test1.mp3'
                                        })

        songB = data[1]
        self.assertEqual(songB['id'], 2)
        self.assertEqual(songB['file'], {'name': 'test2.mp3',
                                         'id': 2,
                                         'path': '/uploads/test2.mp3'
                                        })

    def test_post_song(self):
        """ Adding a new song """
        fileA = models.File(name="test-feb14.mp3")
        session.add(fileA)
        session.commit()

        data = {
            "file": {
                "id": 1
            }
        }

        response = self.client.post("/api/songs",
            data=json.dumps(data),
            content_type="application/json",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.mimetype, "application/json")
        self.assertEqual(urlparse(response.headers.get("Location")).path,
                         "/api/songs/1")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(data['id'], 1)
        self.assertEqual(data['file']['name'], 'test-feb14.mp3')

        file = session.query(models.File).all()
        song = session.query(models.Song).all()
        self.assertEqual(len(file), 1)
        self.assertEqual(len(song), 1)
        file = file[0]
        song = song[0]
        print(file)
        self.assertEqual(file.id, 1)
        self.assertEqual(file.name, 'test-feb14.mp3')
        self.assertEqual(song.id, 1)
        self.assertEqual(song.file, file)

    def test_get_uploaded_file(self):
        path = upload_path("test.txt")
        with open(path, "wb") as f:
            f.write(b"File contents")

        response = self.client.get("/uploads/test.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/plain")
        self.assertEqual(response.data, b"File contents")

    def test_file_upload(self):
        data = {"file": (BytesIO(b"File contents"), "test.txt")}

        response = self.client.post("/api/files",
            data = data,
            content_type = "multipart/form-data",
            headers=[("Accept", "application/json")]
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.mimetype, "application/json")

        data = json.loads(response.data.decode("ascii"))
        self.assertEqual(urlparse(data["path"]).path, "/uploads/test.txt")

        path = upload_path("test.txt")
        self.assertTrue(os.path.isfile(path))
        with open(path, "rb") as f:
            contents = f.read()
        self.assertEqual(contents, b"File contents")

    def tearDown(self):
        """ Test teardown """
        session.close()
        # Remove the tables and their data from the database
        Base.metadata.drop_all(engine)

        # Delete test upload folder
        shutil.rmtree(upload_path())
