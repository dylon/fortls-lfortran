from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
# import asyncio
# import fs
# import json
# import re
# import time
# import uuid
# from json import JSONDecodeError
# from typing import Optional

from lsprotocol import types as lsp

from pygls.protocol import LanguageServerProtocol, lsp_method
from pygls.server import LanguageServer

from lflsp.lfortran_accessor import (
    LFortranAccessor,
    LFortranCLIAccessor,
)


class LFortranLanguageServerProtocol(LanguageServerProtocol):

    _server: "LFortranLanguageServer"

    @lsp_method(lsp.INITIALIZE)
    def lsp_initialize(self, params: lsp.InitializeParams) -> lsp.InitializeResult:
        initialize_result: lsp.InitializeResult = super().lsp_initialize(params)
        return initialize_result


class LFortranLanguageServer(LanguageServer):
    # CMD_REGISTER_COMPLETIONS = "registerCompletions"
    # CMD_SHOW_CONFIGURATION_ASYNC = "showConfigurationAsync"
    # CMD_SHOW_CONFIGURATION_CALLBACK = "showConfigurationCallback"
    # CMD_SHOW_CONFIGURATION_THREAD = "showConfigurationThread"
    # CMD_UNREGISTER_COMPLETIONS = "unregisterCompletions"

    CONFIGURATION_SECTION = "FortLSLFortranLanguageServer"

    def __init__(self, *args):
        super().__init__(*args)


server = LFortranLanguageServer("fortls-lfortran", "v0.1")
lfortran: LFortranAccessor = LFortranCLIAccessor(lambda *args, **kwargs: server.show_message_log(*args, **kwargs))


def validate_text_document(ls, text_document):
    uri = text_document.uri
    text = text_document.source
    settings = {
        compiler: {
            lfortranPath: "/home/dylon/.local/bin/lfortran",
            flags: [
                "-I/home/dylon/Workspace/lcompilers/SNAP/src",
                "-I/var/tmp/lfortran"
            ]
        }
    }
    # settings = ls.get_configuration(
    #     lsp.WorkspaceConfigurationParams(
    #         items=[
    #             lsp.ConfigurationItem(
    #                 scope_uri="", section=LFortranLanguageServer.CONFIGURATION_SECTION
    #             )
    #         ]
    #     )
    # ).result(2)[0]
    # diagnostics = lfortran.show_errors(uri, text, settings)
    diagnostics = []

    lsp_start = lsp.Position()
    lsp_start.line = 9
    lsp_start.character = 0

    lsp_end = lsp.Position()
    lsp_end.line = 9
    lsp_end.character = 5

    lsp_range = lsp.Range()
    lsp_range.start = lsp_start
    lsp_range.end = lsp_end

    diagnostic = lsp.Diagnostic()
    diagnostic.message = "Statement or Declaration expected inside program, found Variable name"
    diagnostic.severity = lsp.DiagnosticSeverity.Error
    diagnostic.source = "lfortran"
    diagnostic.range = lsp_range

    diagnostics.append(diagnostic)

    ls.publish_diagnostics(uri, diagnostics)


# @server.feature(
#     lsp.TEXT_DOCUMENT_DIAGNOSTIC,
#     lsp.DiagnosticOptions(
#         identifier="fortls-lfortran",
#         inter_file_dependencies=True,
#         workspace_diagnostics=True,
#     ),
# )
# def text_document_diagnostic(
#         ls,
#         params: lsp.DocumentDiagnosticParams,
# ) -> lsp.DocumentDiagnosticReport:
#     """Returns diagnostic report."""
#     ls.show_message("text_document_diagnostic")
#     ls.show_message_log("text_document_diagnostic")
#     text_document = server.workspace.get_text_document(params.text_document.uri)
#     ls.show_message(f"text_document_diagnostic.uri = {text_document.uri}")
#     ls.show_message_log(f"text_document_diagnostic.uri = {text_document.uri}")
#     return lsp.RelatedFullDocumentDiagnosticReport(
#         items=validate_text_document(ls, text_document),
#         kind=lsp.DocumentDiagnosticReportKind.Full,
#     )


# @server.feature(lsp.WORKSPACE_DIAGNOSTIC)
# def workspace_diagnostic(
#         ls,
#         params: lsp.WorkspaceDiagnosticParams,
# ) -> lsp.WorkspaceDiagnosticReport:
#     """Returns diagnostic report."""
#     ls.show_message("workspace_diagnostic")
#     ls.show_message_log("workspace_diagnostic")
#     items = []
#     for uri in server.workspace.text_documents.keys():
#         ls.show_message(f"workspace_diagnostic.uri = {uri}")
#         ls.show_message_log(f"workspace_diagnostic.uri = {uri}")
#         text_document = server.workspace.get_text_document(uri)
#         item = lsp.WorkspaceFullDocumentDiagnosticReport(
#             uri=document.uri,
#             version=document.version,
#             items=validate_text_document(ls, text_document),
#             kind=lsp.DocumentDiagnosticReportKind.Full,
#         )
#         items.append(item)
#     return lsp.WorkspaceDiagnosticReport(items=items)


@server.feature(lsp.WORKSPACE_DID_CHANGE_CONFIGURATION)
def workspace_configuration_did_change(
        ls,
        params: lsp.DidChangeConfigurationParams
) -> None:
    # ls.show_message("workspace_configuration_did_change")
    # ls.show_message_log("workspace_configuration_did_change")
    # for uri in ls.workspace.text_documents.keys():
    #     ls.show_message(f"workspace_diagnostic.uri = {uri}")
    #     ls.show_message_log(f"workspace_diagnostic.uri = {uri}")
    #     text_document = server.workspace.get_text_document(uri)
    #     validate_text_document(ls, text_document)
    pass


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def text_document_did_save(
        ls,
        params: lsp.DidSaveTextDocumentParams
) -> None:
    ls.show_message("text_document_did_save")
    ls.show_message_log("text_document_did_save")
    text_document = server.workspace.get_text_document(params.text_document.uri)
    validate_text_document(ls, text_document)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def text_document_did_change(
        ls,
        params: lsp.DidChangeTextDocumentParams
) -> None:
    ls.show_message("text_document_did_change")
    ls.show_message_log("text_document_did_change")
    text_document = server.workspace.get_text_document(params.text_document.uri)
    validate_text_document(ls, text_document)


@server.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
def text_document_did_close(
        ls,
        params: lsp.DidCloseTextDocumentParams
) -> None:
    ls.show_message("text_document_did_close")
    ls.show_message_log("text_document_did_close")


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
async def text_document_did_open(
        ls,
        params: lsp.DidOpenTextDocumentParams
) -> None:
    ls.show_message("text_document_did_open")
    ls.show_message_log("text_document_did_open")
    text_document = server.workspace.get_text_document(params.text_document.uri)
    validate_text_document(ls, text_document)


# @server.feature(
#     lsp.TEXT_DOCUMENT_COMPLETION,
#     lsp.CompletionOptions(trigger_characters=[","], all_commit_characters=[":"]),
# )
# def completions(params: Optional[lsp.CompletionParams] = None) -> lsp.CompletionList:
#     """Returns completion items."""
#     return lsp.CompletionList(
#         is_incomplete=False,
#         items=[
#             lsp.CompletionItem(label='"'),
#             lsp.CompletionItem(label="["),
#             lsp.CompletionItem(label="]"),
#             lsp.CompletionItem(label="{"),
#             lsp.CompletionItem(label="}"),
#         ],
#     )


# @server.feature(
#     lsp.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
#     lsp.SemanticTokensLegend(token_types=["operator"], token_modifiers=[]),
# )
# def semantic_tokens(ls: LFortranLanguageServer, params: lsp.SemanticTokensParams):
#     """See https://microsoft.github.io/language-server-protocol/specification#textDocument_semanticTokens
#     for details on how semantic tokens are encoded."""

#     TOKENS = re.compile('".*"(?=:)')

#     uri = params.text_document.uri
#     doc = server.workspace.get_document(uri)

#     last_line = 0
#     last_start = 0

#     data = []

#     for lineno, line in enumerate(doc.lines):
#         last_start = 0

#         for match in TOKENS.finditer(line):
#             start, end = match.span()
#             data += [(lineno - last_line), (start - last_start), (end - start), 0, 0]

#             last_line = lineno
#             last_start = start

#     return lsp.SemanticTokens(data=data)


# @server.feature(lsp.TEXT_DOCUMENT_INLINE_VALUE)
# def inline_value(params: lsp.InlineValueParams):
#     """Returns inline value."""
#     return [lsp.InlineValueText(range=params.range, text="Inline value")]


# @server.command(LFortranLanguageServer.CMD_REGISTER_COMPLETIONS)
# async def register_completions(ls: LFortranLanguageServer, *args):
#     """Register completions method on the client."""
#     params = lsp.RegistrationParams(
#         registrations=[
#             lsp.Registration(
#                 id=str(uuid.uuid4()),
#                 method=lsp.TEXT_DOCUMENT_COMPLETION,
#                 register_options={"triggerCharacters": "[':']"},
#             )
#         ]
#     )
#     response = await server.register_capability_async(params)
#     if response is None:
#         server.show_message("Successfully registered completions method")
#     else:
#         server.show_message(
#             "Error happened during completions registration.", lsp.MessageType.Error
#         )


# @server.command(LFortranLanguageServer.CMD_SHOW_CONFIGURATION_ASYNC)
# async def show_configuration_async(ls: LFortranLanguageServer, *args):
#     """Gets exampleConfiguration from the client settings using coroutines."""
#     try:
#         config = await server.get_configuration_async(
#             lsp.WorkspaceConfigurationParams(
#                 items=[
#                     lsp.ConfigurationItem(
#                         scope_uri="", section=LFortranLanguageServer.CONFIGURATION_SECTION
#                     )
#                 ]
#             )
#         )

#         example_config = config[0].get("exampleConfiguration")

#         server.show_message(f"jsonServer.exampleConfiguration value: {example_config}")

#     except Exception as e:
#         server.show_message_log(f"Error ocurred: {e}")


# @server.command(LFortranLanguageServer.CMD_SHOW_CONFIGURATION_CALLBACK)
# def show_configuration_callback(ls: LFortranLanguageServer, *args):
#     """Gets exampleConfiguration from the client settings using callback."""

#     def _config_callback(config):
#         try:
#             example_config = config[0].get("exampleConfiguration")

#             server.show_message(f"jsonServer.exampleConfiguration value: {example_config}")

#         except Exception as e:
#             server.show_message_log(f"Error ocurred: {e}")

#     server.get_configuration(
#         lsp.WorkspaceConfigurationParams(
#             items=[
#                 lsp.ConfigurationItem(
#                     scope_uri="", section=LFortranLanguageServer.CONFIGURATION_SECTION
#                 )
#             ]
#         ),
#         _config_callback,
#     )


# @server.thread()
# @server.command(LFortranLanguageServer.CMD_SHOW_CONFIGURATION_THREAD)
# def show_configuration_thread(ls: LFortranLanguageServer, *args):
#     """Gets exampleConfiguration from the client settings using thread pool."""
#     try:
#         config = server.get_configuration(
#             lsp.WorkspaceConfigurationParams(
#                 items=[
#                     lsp.ConfigurationItem(
#                         scope_uri="", section=LFortranLanguageServer.CONFIGURATION_SECTION
#                     )
#                 ]
#             )
#         ).result(2)

#         example_config = config[0].get("exampleConfiguration")

#         server.show_message(f"jsonServer.exampleConfiguration value: {example_config}")

#     except Exception as e:
#         server.show_message_log(f"Error ocurred: {e}")


# @server.command(LFortranLanguageServer.CMD_UNREGISTER_COMPLETIONS)
# async def unregister_completions(ls: LFortranLanguageServer, *args):
#     """Unregister completions method on the client."""
#     params = lsp.UnregistrationParams(
#         unregisterations=[
#             lsp.Unregistration(
#                 id=str(uuid.uuid4()), method=lsp.TEXT_DOCUMENT_COMPLETION
#             )
#         ]
#     )
#     response = await server.unregister_capability_async(params)
#     if response is None:
#         server.show_message("Successfully unregistered completions method")
#     else:
#         server.show_message(
#             "Error happened during completions unregistration.", lsp.MessageType.Error
#         )


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
