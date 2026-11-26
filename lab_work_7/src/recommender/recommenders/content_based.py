
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ContentBasedRecommender:
    def fit(self, train: pd.DataFrame, movies: pd.DataFrame):
        self.movies = movies.copy()

        # Объединяем название и жанры в единый текстовый признак.
        self.movies["content"] = (
            self.movies["title"].fillna("")
            + " "
            + self.movies["genres"].fillna("").str.replace("|", " ", regex=False)
        )

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english"
        )

        self.item_matrix = self.vectorizer.fit_transform(
            self.movies["content"]
        )

        self.movie_ids = self.movies["movieId"].tolist()
        self.id_to_index = {
            movie_id: index
            for index, movie_id in enumerate(self.movie_ids)
        }

        self.rated_by_user = (
            train.groupby("userId")["movieId"].apply(set).to_dict()
        )

        self.positive_train = train[train["rating"] >= 4.0]

        self.user_likes = (
            self.positive_train.groupby("userId")
            .apply(
                lambda group: list(
                    zip(group["movieId"], group["rating"])
                )
            )
            .to_dict()
        )

        return self

    def recommend(self, user_id: int, k: int = 10):
        liked_items = self.user_likes.get(user_id, [])

        if not liked_items:
            return []

        # Формируем профиль пользователя как взвешенную сумму
        # TF-IDF-векторов понравившихся фильмов.
        profile = None

        for movie_id, rating in liked_items:
            index = self.id_to_index.get(movie_id)

            if index is None:
                continue

            weight = rating - 3.0
            vector = self.item_matrix[index] * weight

            profile = vector if profile is None else profile + vector

        if profile is None:
            return []

        scores = cosine_similarity(profile, self.item_matrix).ravel()

        seen_items = self.rated_by_user.get(user_id, set())

        candidates = [
            (self.movie_ids[index], scores[index])
            for index in range(len(self.movie_ids))
            if self.movie_ids[index] not in seen_items
        ]

        candidates.sort(key=lambda x: x[1], reverse=True)

        return [movie_id for movie_id, score in candidates[:k]]
