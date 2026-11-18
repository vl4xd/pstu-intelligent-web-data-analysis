
class WikimediaError(Exception):
    """Базовая ошибка приложения."""
    pass


class NetworkError(WikimediaError):
    """Проблемы с подключением к серверу."""
    pass


class ServerUnavailableError(WikimediaError):
    """Сервер временно недоступен."""
    pass


class RateLimitError(WikimediaError):
    """Превышено ограничение запросов."""
    pass


class APIError(WikimediaError):
    """Ошибка, возвращённая Wikimedia API."""
    pass


class InvalidResponseError(WikimediaError):
    """Некорректный ответ API."""
    pass


class ArticleNotFoundError(WikimediaError):
    """Статья не найдена."""
    pass
