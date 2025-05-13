"""Request utils."""


def url_join(*args) -> str:  # noqa: ANN002
    """Join url parts."""
    return '/'.join(args).replace('//', '/').replace(':/', '://')
