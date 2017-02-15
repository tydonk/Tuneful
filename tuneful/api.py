import os.path
import json

from flask import request, Response, url_for, send_from_directory
from werkzeug.utils import secure_filename
from jsonschema import validate, ValidationError

from . import models
from . import decorators
from tuneful import app
from .database import session
from .utils import upload_path

# JSON Schema describing the song structure
song_schema = {
    "definitions": {
        "file": {
            "type": "object",
            "properties": {
                "id": {"type": "number"}
            }
        }
    }
}

@app.route("/api/songs", methods=["GET"])
@decorators.accept("application/json")
def get_songs():
    """ Return all songs """
    # Get the songs from the database
    songs = session.query(models.Song)

    # Convert song data to JSON and return a response
    data = json.dumps([song.as_dict() for song in songs])
    return Response(data, 200, mimetype="application/json")

@app.route("/api/songs/<int:id>", methods=["GET"])
@decorators.accept("application/json")
def get_song(id):
    """ Return a single song """
    # Get song from database
    song = session.query(models.Song).get(id)

    # Check wether song exists
    # If not return a 404 with a helpful message
    if not song:
        message = "Could not find song with id {}".format(id)
        data = json.dumps({"message": message})
        return Response(data, 404, mimetype="application/json")

    # Return the song as JSON
    data = json.dumps(song.as_dict())
    return Response(data, 200, mimetype="application/json")

@app.route("/api/songs", methods=["POST"])
@decorators.accept("application/json")
@decorators.require("application/json")
def post_song():
    """ Add a new song """
    data = request.json

    # Check that the JSON supplied is valid
    # If not you return a 422 Unprocessable Entity
    try:
        validate(data, song_schema)
    except ValidationError as error:
        data = {"message": error.message}
        return Response(json.dumps(data), 422, mimetype="application/json")

    file = session.query(models.File).get(data['file']['id'])
    if not file:
        message - "Could not find file with id {}".format(data['file']['id'])
        error = json.dumps({"message": message})
        return Response(error, 404, mimetype="application/json")

    # Add the song to the database
    song = models.Song(file=file)
    session.add(song)
    session.commit()

    # Return a 201 Created, containing the song as JSON and with the
    # Location header set to the location of the song
    data = json.dumps(song.as_dict())
    headers = {"Location": url_for("get_song", id=song.id)}
    return Response(data, 201, headers=headers,
                    mimetype="application/json")

@app.route("/uploads/<filename>", methods=["GET"])
def uploaded_file(filename):
    return send_from_directory(upload_path(), filename)

@app.route("/api/files", methods=["POST"])
@decorators.require("multipart/form-data")
@decorators.accept("application/json")
def file_post():
    file = request.files.get("file")
    if not file:
        data = {"message": "Could not find file data"}
        return Response(json.dumps(data), 422, mimetype="application/json")

    filename = secure_filename(file.filename)
    db_file = models.File(name=filename)
    session.add(db_file)
    session.commit()
    file.save(upload_path(filename))

    data = db_file.as_dict()
    return Response(json.dumps(data), 201, mimetype="application/json")
