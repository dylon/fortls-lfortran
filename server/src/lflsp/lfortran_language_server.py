from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
# import asyncio
# import fs
# import json
import logging
# import re
# import time
import traceback
# import uuid
from functools import wraps
# from json import JSONDecodeError
from typing import Any, Dict, Optional

from lsprotocol import types as lsp

from pygls.protocol import LanguageServerProtocol, lsp_method
from pygls.server import LanguageServer

from lflsp.lfortran_accessor import (
    LFortranAccessor,
    LFortranCLIAccessor,
)


logging.basicConfig(filename='/var/tmp/pygls.log', filemode='w', level=logging.DEBUG)
logger = logging.getLogger(__name__)


def catch_and_log_exception(fn):
    @wraps(fn)
    async def wrapper(ls, *args, **kwargs):
        try:
            retval = await fn(ls, *args, **kwargs)
            return retval
        except Exception:
            stack_trace = traceback.format_exc()
            ls.show_message_log(stack_trace)
    return wrapper


class LFortranLanguageServerProtocol(LanguageServerProtocol):

    _server: "LFortranLanguageServer"

    @lsp_method(lsp.INITIALIZE)
    def lsp_initialize(self, params: lsp.InitializeParams) -> lsp.InitializeResult:
        # If necessary, customize the initialization logic, here.
        result: lsp.InitializeResult = super().lsp_initialize(params)
        return result


class LFortranLanguageServer(LanguageServer):
    CONFIGURATION_SECTION = "FortLSLFortranLanguageServer"

    settings: Optional[Dict[str, Any]] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


server = LFortranLanguageServer(
    name="fortls-lfortran",
    version="v0.1",
    protocol_cls=LFortranLanguageServerProtocol
)

def show_message_log(*args, **kwargs):
    server.show_message_log(*args, **kwargs)

lfortran: LFortranAccessor = LFortranCLIAccessor(show_message_log)


async def validate_text_document(ls, text_document) -> None:
    uri = text_document.uri
    text = text_document.source
    settings = await ls.get_configuration_async(lsp.WorkspaceConfigurationParams([
        lsp.ConfigurationItem(
            scope_uri=uri,
            section=LFortranLanguageServer.CONFIGURATION_SECTION
        ),
    ]))
    diagnostics = lfortran.show_errors(uri, text, settings[0])
    ls.publish_diagnostics(uri, diagnostics)


@server.feature(lsp.WORKSPACE_DID_CHANGE_CONFIGURATION)
@catch_and_log_exception
async def workspace_configuration_did_change(
        ls,
        params: lsp.DidChangeConfigurationParams
) -> None:
    for uri in ls.workspace.text_documents.keys():
        text_document = server.workspace.get_text_document(uri)
        await validate_text_document(ls, text_document)


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
@catch_and_log_exception
async def text_document_did_save(
        ls,
        params: lsp.DidSaveTextDocumentParams
) -> None:
    text_document = server.workspace.get_text_document(params.text_document.uri)
    await validate_text_document(ls, text_document)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
@catch_and_log_exception
async def text_document_did_change(
        ls,
        params: lsp.DidChangeTextDocumentParams
) -> None:
    text_document = server.workspace.get_text_document(params.text_document.uri)
    await validate_text_document(ls, text_document)


@server.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
@catch_and_log_exception
async def text_document_did_close(
        ls,
        params: lsp.DidCloseTextDocumentParams
) -> None:
    pass


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
@catch_and_log_exception
async def text_document_did_open(
        ls,
        params: lsp.DidOpenTextDocumentParams
) -> None:
    text_document = server.workspace.get_text_document(params.text_document.uri)
    await validate_text_document(ls, text_document)


def add_arguments(parser):
    parser.description = "Serves LSP requests with responses from LFortran."
    parser.add_argument("--tcp", action="store_true", help="Use TCP server")
    parser.add_argument("--ws", action="store_true", help="Use WebSocket server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind to this address")
    parser.add_argument("--port", type=int, default=2087, help="Bind to this port")


def main():
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args()

    if args.tcp:
        server.start_tcp(args.host, args.port)
    elif args.ws:
        server.start_ws(args.host, args.port)
    else:
        server.start_io()


if __name__ == "__main__":
    main()
