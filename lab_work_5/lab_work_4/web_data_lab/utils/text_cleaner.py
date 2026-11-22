
import ftfy


def clean_text(value):
    """Исправляет кодировку, удаляет лишние пробелы и приводит текст к нижнему регистру."""
    if not isinstance(value, str):
        return value

    value = ftfy.fix_text(value)
    value = value.strip()
    value = " ".join(value.split())
    value = value.lower()

    return value
