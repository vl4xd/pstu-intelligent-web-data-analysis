import numpy as np
from gensim.corpora.dictionary import Dictionary
from gensim.models.coherencemodel import CoherenceModel
from sklearn.decomposition import LatentDirichletAllocation, NMF
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer


def calculate_coherence(model, feature_names, tokenized_texts, top_n=10):
    """Расчёт C_v Coherence через Gensim."""
    topics = []
    for topic in model.components_:
        top_ind = topic.argsort()[:-top_n - 1:-1]
        topics.append([feature_names[i] for i in top_ind])

    dictionary = Dictionary(tokenized_texts)
    dictionary.filter_extremes(no_below=1, no_above=0.95)

    cm = CoherenceModel(
        topics=topics,
        texts=tokenized_texts,
        dictionary=dictionary,
        coherence="c_v",
    )
    return cm.get_coherence()


def train_model(texts, tokenized_texts, method, n_topics, max_features=1000):
    """
    Обучает LDA (на CountVectorizer) или NMF (на TfidfVectorizer).
    Возвращает: model, vectorizer, feature_names, coherence.
    """
    if method == "lda":
        vec = CountVectorizer(
            max_features=max_features,
            max_df=0.6, # <--- Игнорировать слова, которые есть в >60% документов
            min_df=2    # <--- Игнорировать слова, которые есть < чем в 2 документах (опечатки)
        )
        X = vec.fit_transform(texts)
        model = LatentDirichletAllocation(
            n_components=n_topics,
            random_state=42,
            max_iter=10,
        )
    elif method == "nmf":
        vec = TfidfVectorizer(max_features=max_features, max_df=0.5, min_df=2)
        X = vec.fit_transform(texts)
        model = NMF(n_components=n_topics, random_state=42)
    else:
        raise ValueError("method должен быть 'lda' или 'nmf'")

    model.fit(X)
    feature_names = vec.get_feature_names_out()
    coherence = calculate_coherence(model, feature_names, tokenized_texts)
    return model, vec, feature_names, coherence


def find_best_k(texts, tokenized_texts, method, min_k=3, max_k=20):
    """Перебор K и поиск максимума Coherence."""
    scores = []
    k_values = list(range(min_k, max_k + 1))

    for k in k_values:
        print(f"  Тест K={k} ({method.upper()})...")
        try:
            _, _, _, score = train_model(texts, tokenized_texts, method, k)
            scores.append(score)
        except Exception as e:
            print(f"  Ошибка при K={k}: {e}")
            scores.append(-1.0)

    best_idx = int(np.argmax(scores))
    best_k = k_values[best_idx]

    if best_k == max_k:
        print(f"⚠️  Оптимум K={best_k} на верхней границе диапазона. "
              f"Попробуйте --max-k {max_k + 10}.")
    elif best_k == min_k:
        print(f"⚠️  Оптимум K={best_k} на нижней границе диапазона.")
        
    return best_k, k_values, scores