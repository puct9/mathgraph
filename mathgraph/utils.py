import inspect

from .operations import Input, Operation


def compile_operation(func) -> Operation:
    params = inspect.signature(func).parameters
    kwargs = {}
    for param in params:
        kwargs[param] = Input(param)
    return func(**kwargs)
