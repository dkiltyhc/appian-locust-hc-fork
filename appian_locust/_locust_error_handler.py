from functools import wraps
from typing import Any, Callable, Optional

from locust.clients import ResponseContextManager
from requests.exceptions import HTTPError

from appian_locust.helper import ENV

from . import logger

log = logger.getLogger(__name__)


def test_response_for_error(resp: ResponseContextManager, uri: str = 'No URI Specified', raise_error: bool = True, username: str = "") -> None:
    """
    Locust relies on errors to be logged to the global_stats attribute for error handling.
    This function is used to notify Locust that its instances are failing and that it should fail too.

    Args:
        resp (Response): a python response object from a client.get() or client.post() call in Locust tests.
        uri (Str): URI in the request that caused the above response.
        username (Str): identifies the current user when we use multiple different users for locust test)

    Returns:
        None

    Example (Returns a HTTP 500 error):

    .. code-block:: python

      uri = 'https://httpbin.org/status/500'
      with self.client.get(uri) as resp:
        test_response_for_error(resp, uri)
    """
    try:
        if not resp or not resp.ok:
            error = HTTPError(f'HTTP ERROR CODE: {resp.status_code} MESSAGE: {resp.text} USERNAME: {username}')
            resp.failure(error)
            # TODO: Consider using this resp.failure construct in other parts of the code
            log_locust_error(
                error,
                'REQUEST:',
                f'URI: {resp.url}',
                raise_error=raise_error
            )
    except HTTPError as e:
        raise e
    except Exception as e:
        log_locust_error(
            Exception(f'MESSAGE: {e}'),
            'REQUEST:',
            f'URI: {resp.url}',
            raise_error=True
        )


def log_locust_error(e: Exception, error_desc: str = 'No description', location: str = 'No location', raise_error: bool = True) -> None:
    """
    This function allows scripts in appian_locust to manually report an error to locust.

    Args:
        e (Exception): whichever error occured should be propagated through this variable.
        error_desc (str): contains information about the error.
        location (str): URI or current working directory that contains the location of the error.

    Returns:
        None

    Example:

    .. code-block:: python

        if not current_news:
            e = Exception(f"News object: {current} news does not exist.")
            desc = f'Error in get_news function'
            log_locust_error(e, error_desc=desc)
    """
    ENV.stats.log_error(f'DESC: {error_desc}', f'LOCATION: {location}', f'EXCEPTION: {e}')

    if raise_error:
        raise e


def raises_locust_error(location: str) -> Callable:
    def should_log_loc_error(func: Callable) -> Callable:
        @wraps(func)
        def func_wrapper(*args: Any, **kwargs: Any) -> Optional[Callable]:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_locust_error(e, location=location, raise_error=True)
                return None
        return func_wrapper
    return should_log_loc_error
