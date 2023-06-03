class SendMessageFailException(Exception):
    """Исключение, когда не удалось выслать сообщение."""

    pass


class HTTPStatusNotOKException(Exception):
    """Исключение, когда код ответа сервера не равен 200."""

    pass


class HomeworkOrTimestampException(Exception):
    """Отсутствует домашняя работа или timestamp."""

    pass
