from .base import *  # noqa: F403


DEBUG = True

ALLOWED_HOSTS = env_list(  # noqa: F405
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,0.0.0.0",
)

CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)  # noqa: F405
