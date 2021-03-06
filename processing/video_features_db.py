import pickle
from dataclasses import dataclass
from typing import List

from bson import Binary
from pymongo import MongoClient

from logger_wrapper import Log, LogLevel


def npArray2Binary(npArray):
    """Utility method to turn an numpy array into a BSON Binary string.
    utilizes pickle protocol 2 (see http://www.python.org/dev/peps/pep-0307/
    for more details).
    Called by stashNPArrays.
    :param npArray: numpy array of arbitrary dimension or a list of npArrays
    :returns: BSON Binary object a pickled numpy array (or a list).
    """

    if type(npArray) is list:
        return [Binary(pickle.dumps(f_vec)) for f_vec in npArray]

    return Binary(pickle.dumps(npArray, protocol=2), subtype=128)


def binary2npArray(binary):
    """Utility method to turn a a pickled numpy array string back into
    a numpy array.
    Called by loadNPArrays, and thus by loadFullData and loadFullExperiment.
    :param binary: BSON Binary object a pickled numpy array or a list of objects.
    :returns: numpy array of arbitrary dimension (or a list)
    """

    if type(binary) is list:
        return [pickle.loads(b_vec) for b_vec in binary]

    return pickle.loads(binary)


@dataclass
class VideoFeatures(dict):
    name: str
    feature_vectors: list
    original_video_url: str
    duration: int
    _id: str = None


class VideoFeaturesDb:
    _COLLECTION_NAME: str = 'VideoFeatures'
    _DB_NAME: str = 'VideosDB'

    def __init__(self, verbose: bool = False) -> None:
        mongo_client = MongoClient(host='localhost', port=27017, document_class=dict)
        self._db = mongo_client[self._DB_NAME]
        self._log = Log(level=LogLevel.DEBUG if verbose else None)

    def get_all_video_features(self) -> List[VideoFeatures]:
        self._log.debug('Fetching all persisted video info...')

        fetch_result = self._db[self._COLLECTION_NAME].find()

        return [
            VideoFeatures(
                name=persistent_video['name'],
                feature_vectors=binary2npArray(persistent_video['feature_vectors']),
                original_video_url=persistent_video['original_video_url'],
                duration=persistent_video['duration'],
                _id=persistent_video['_id']
            )
            for persistent_video in fetch_result
        ]

    def get_all_processed_videos_info(self) -> List[dict]:
        self._log.debug('Fetching all persisted video info...')

        fetch_result = self._db[self._COLLECTION_NAME].aggregate(pipeline=[
            {
                '$project': {
                    'feature_vectors_count': {'$size': '$feature_vectors'},
                    'name': 1,
                    'duration': 1,
                    '_id': 0,
                    'original_video_url': 1
                }
            }
        ])

        return list(fetch_result)

    def get_video_features_by_name(self, search_name: str) -> VideoFeatures:
        self._log.debug(f'Searching persisted video info with name {search_name}')

        persistent_video = self._db[self._COLLECTION_NAME].find_one(filter={'name': search_name})

        return VideoFeatures(
            name=persistent_video['name'],
            feature_vectors=binary2npArray(persistent_video['feature_vectors']),
            original_video_url=persistent_video['original_video_url'],
            duration=persistent_video['duration'],
            _id=persistent_video['_id']
        )

    def save_processed_video(self, video_features: VideoFeatures):
        self._log.debug(f'Saving processed video info: {video_features}')

        dict_values = video_features.__dict__
        del dict_values['_id']
        dict_values['feature_vectors'] = npArray2Binary(dict_values['feature_vectors'])
        self._db[self._COLLECTION_NAME].insert_one(video_features.__dict__)

    def update_processed_video(self, video_features: VideoFeatures):
        self._log.debug(f'Updating processed video info: {video_features}')

        dict_values = video_features.__dict__
        dict_values['feature_vectors'] = npArray2Binary(dict_values['feature_vectors'])
        self._db[self._COLLECTION_NAME].update_one(video_features.__dict__)
