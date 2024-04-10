from annoy import AnnoyIndex

class SongDB:
    def __init__(self, n_features):
        self.n_features = n_features
        self.annoy_index = AnnoyIndex(n_features, 'angular')

    def add_track(self, track):
        features = []
        for feature in track.features.values():
            if type(feature) == float:
                features.append(int(feature * 1000))
            elif type(feature) == int:
                features.append(feature)
        self.annoy_index.add_item(track.db_id, features)

    def build(self, n_trees=10):
        self.annoy_index.build(n_trees)

    def get_similar(self, song_id, n=5):
        return self.annoy_index.get_nns_by_item(song_id, n)

    def save(self, path):
        self.annoy_index.save(path)

    @classmethod
    def load(cls, path, n_features):
        song_db = cls(n_features)
        song_db.annoy_index.load(path)
        return song_db