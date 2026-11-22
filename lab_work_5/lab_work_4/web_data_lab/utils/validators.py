
def validate_item(item, required_fields=None):
    """Проверяет наличие обязательных полей в записи."""

    if required_fields is None:
        required_fields = ["title", "url"]

    for field in required_fields:
        value = item.get(field)

        if value is None:
            return False

        if isinstance(value, str) and not value.strip():
            return False

    return True
