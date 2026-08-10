"""Shared test fixtures and compatibility shims.

Installs a small aioresponses/aiohttp compatibility shim; see
``_patch_client_response_for_aioresponses`` below.
"""

from __future__ import annotations

import inspect
from typing import Any

from aiohttp.client_reqrep import ClientResponse


class _NullStreamWriter:
    """Stand-in for the stream writer aiohttp>=3.13 reads on construction.

    A mocked response is never actually written to the wire, so aiohttp only
    reads ``output_size`` off this object (client_reqrep records it when the
    request was "already sent").
    """

    output_size = 0


def _patch_client_response_for_aioresponses() -> None:
    """Let aioresponses build responses on aiohttp>=3.13.

    aiohttp 3.13 added a required keyword-only ``stream_writer`` argument to
    ``ClientResponse.__init__``. aioresponses (through 0.7.9, current) does
    not pass it, so every mocked request in tests/test_client.py dies with::

        TypeError: ClientResponse.__init__() missing 1 required
        keyword-only argument: 'stream_writer'

    Default that kwarg rather than capping the test-time aiohttp: this
    integration's runtime dependency is uncapped, so pinning the tests to an
    old aiohttp would mean never exercising the version users actually run.

    The shim is self-limiting in both directions -- on aiohttp<3.13 the
    parameter does not exist and we skip patching entirely, and once
    aioresponses passes ``stream_writer`` itself the ``setdefault`` becomes a
    no-op. Remove it once aioresponses supports aiohttp>=3.13 natively.
    """
    if "stream_writer" not in inspect.signature(ClientResponse.__init__).parameters:
        return

    original_init = ClientResponse.__init__

    def _init(self: ClientResponse, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("stream_writer", _NullStreamWriter())
        original_init(self, *args, **kwargs)

    ClientResponse.__init__ = _init  # type: ignore[method-assign]


_patch_client_response_for_aioresponses()
