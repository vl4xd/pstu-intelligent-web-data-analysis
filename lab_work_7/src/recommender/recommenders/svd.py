
import pandas as pd
from surprise import Dataset, Reader, SVD


class SVDRecommender:
    def fit(self, train: pd.DataFrame):
        reader = Reader(rating_scale=(0.5, 5.0))
        data = Dataset.load_from_df(
            train[["userId", "movieId", "rating"]],
            reader
        )

        trainset = data.build_full_trainset()

        self.model = SVD(
            n_factors=100,
            n_epochs=20,
            lr_all=0.005,
            reg_all=0.02,
            random_state=42
        )

        self.model.fit(trainset)

        self.trainset = trainset
        self.rated_by_user = (
            train.groupby("userId")["movieId"].apply(set).to_dict()
        )

        self.all_items = train["movieId"].unique().tolist()

        return self

    def recommend(self, user_id: int, k: int = 10):
        seen_items = self.rated_by_user.get(user_id, set())

        candidates = [
            movie_id
            for movie_id in self.all_items
            if movie_id not in seen_items
        ]

        predictions = [
            (
                movie_id,
                self.model.predict(user_id, movie_id).est
            )
            for movie_id in candidates
        ]

        predictions.sort(key=lambda x: x[1], reverse=True)

        return [
            movie_id
            for movie_id, score in predictions[:k]
        ]
