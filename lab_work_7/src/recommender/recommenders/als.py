
from threadpoolctl import threadpool_limits
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from implicit.als import AlternatingLeastSquares

threadpool_limits(limits=1, user_api="blas")


class ALSRecommender:
    def fit(self, train: pd.DataFrame):
        # Оставляем только положительные взаимодействия.
        positive = train[train["rating"] >= 4.0].copy()

        self.user_ids = sorted(train["userId"].unique())
        self.item_ids = sorted(train["movieId"].unique())

        self.user_to_index = {
            user_id: index
            for index, user_id in enumerate(self.user_ids)
        }
        self.item_to_index = {
            item_id: index
            for index, item_id in enumerate(self.item_ids)
        }

        rows = positive["userId"].map(self.user_to_index).to_numpy()
        cols = positive["movieId"].map(self.item_to_index).to_numpy()

        # Веса взаимодействий: оценка выше порога даёт положительный сигнал.
        values = (
            positive["rating"].to_numpy(dtype=np.float32) - 3.0
        )

        user_items = csr_matrix(
            (values, (rows, cols)),
            shape=(len(self.user_ids), len(self.item_ids)),
            dtype=np.float32
        )

        self.user_items = user_items

        self.model = AlternatingLeastSquares(
            factors=64,
            regularization=0.1,
            iterations=20,
            random_state=42
        )

        # implicit ALS ожидает матрицу user-item.
        self.model.fit(user_items)

        self.rated_by_user = (
            train.groupby("userId")["movieId"].apply(set).to_dict()
        )

        return self

    def recommend(self, user_id: int, k: int = 10):
        user_index = self.user_to_index.get(user_id)

        if user_index is None:
            return []

        item_indices, scores = self.model.recommend(
            userid=user_index,
            user_items=self.user_items[user_index],
            N=len(self.item_ids),
            filter_already_liked_items=False
        )

        seen_items = self.rated_by_user.get(user_id, set())

        ranked = [
            (self.item_ids[int(index)], float(score))
            for index, score in zip(item_indices, scores)
            if self.item_ids[int(index)] not in seen_items
        ]

        return [movie_id for movie_id, score in ranked[:k]]
