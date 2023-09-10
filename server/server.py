import asyncio
import re
import time
import uuid
from typing import Optional

from .utils.validation import _validate
from .utils.completion import _get_completion_items

from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_CLOSE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,

)
from lsprotocol.types import (
    CompletionList,
    CompletionOptions,
    CompletionParams,
    ConfigurationItem,
    DidChangeTextDocumentParams,
    DidCloseTextDocumentParams,
    DidOpenTextDocumentParams,
    MessageType,
    Registration,
    RegistrationParams,
    SemanticTokens,
    SemanticTokensLegend,
    SemanticTokensParams,
    Unregistration,
    UnregistrationParams,
    WorkDoneProgressBegin,
    WorkDoneProgressEnd,
    WorkDoneProgressReport,
    WorkspaceConfigurationParams,
)
from pygls.server import LanguageServer

COUNT_DOWN_START_IN_SECONDS = 10
COUNT_DOWN_SLEEP_IN_SECONDS = 1


class JaclangLanguageServer(LanguageServer):
    CMD_COUNT_DOWN_BLOCKING = "countDownBlocking"
    CMD_COUNT_DOWN_NON_BLOCKING = "countDownNonBlocking"
    CMD_PROGRESS = "progress"
    CMD_REGISTER_COMPLETIONS = "registerCompletions"
    CMD_SHOW_CONFIGURATION_ASYNC = "showConfigurationAsync"
    CMD_SHOW_CONFIGURATION_CALLBACK = "showConfigurationCallback"
    CMD_SHOW_CONFIGURATION_THREAD = "showConfigurationThread"
    CMD_UNREGISTER_COMPLETIONS = "unregisterCompletions"

    CONFIGURATION_SECTION = "jaclangServer"

    def __init__(self, *args):
        super().__init__(*args)


jaclang_server = JaclangLanguageServer("pygls-jaclang", "v0.0.1-alpha")


@jaclang_server.feature(TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls, params: DidChangeTextDocumentParams):
    """Stuff to happen on text document did change"""
    ls.show_message("Text Document Did Change")
    _validate(ls, params)


@jaclang_server.feature(TEXT_DOCUMENT_DID_CLOSE)
def did_close(server: JaclangLanguageServer, params: DidCloseTextDocumentParams):
    """Stuff to happen on text document did close"""
    server.show_message("Text Document Did Close")


@jaclang_server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls, params: DidOpenTextDocumentParams):
    """Stuff to happen on text document did open"""
    ls.show_message("Text Document Did Open")
    _validate(ls, params)


@jaclang_server.feature(
    TEXT_DOCUMENT_COMPLETION, CompletionOptions(trigger_characters=[":", "::", "."])
)
def completions(params: Optional[CompletionParams] = None) -> CompletionList:
    """Returns completion items."""
    completion_items = _get_completion_items(jaclang_server, params)
    return CompletionList(is_incomplete=False, items=completion_items)


@jaclang_server.command(JaclangLanguageServer.CMD_COUNT_DOWN_BLOCKING)
def count_down_10_seconds_blocking(ls, *args):
    """Starts counting down and showing message synchronously.
    It will `block` the main thread, which can be tested by trying to show
    completion items.
    """
    for i in range(COUNT_DOWN_START_IN_SECONDS):
        ls.show_message(f"Counting down... {COUNT_DOWN_START_IN_SECONDS - i}")
        time.sleep(COUNT_DOWN_SLEEP_IN_SECONDS)


@jaclang_server.command(JaclangLanguageServer.CMD_COUNT_DOWN_NON_BLOCKING)
async def count_down_10_seconds_non_blocking(ls, *args):
    """Starts counting down and showing message asynchronously.
    It won't `block` the main thread, which can be tested by trying to show
    completion items.
    """
    for i in range(COUNT_DOWN_START_IN_SECONDS):
        ls.show_message(f"Counting down... {COUNT_DOWN_START_IN_SECONDS - i}")
        await asyncio.sleep(COUNT_DOWN_SLEEP_IN_SECONDS)


@jaclang_server.feature(
    TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    SemanticTokensLegend(token_types=["operator"], token_modifiers=[]),
)
def semantic_tokens(ls: JaclangLanguageServer, params: SemanticTokensParams):
    """See https://microsoft.github.io/language-server-protocol/specification#textDocument_semanticTokens
    for details on how semantic tokens are encoded."""

    TOKENS = re.compile('".*"(?=:)')

    uri = params.text_document.uri
    doc = ls.workspace.get_document(uri)

    last_line = 0
    last_start = 0

    data = []

    for lineno, line in enumerate(doc.lines):
        last_start = 0

        for match in TOKENS.finditer(line):
            start, end = match.span()
            data += [(lineno - last_line), (start - last_start), (end - start), 0, 0]

            last_line = lineno
            last_start = start

    return SemanticTokens(data=data)


@jaclang_server.command(JaclangLanguageServer.CMD_PROGRESS)
async def progress(ls: JaclangLanguageServer, *args):
    """Create and start the progress on the client."""
    token = str(uuid.uuid4())
    # Create
    await ls.progress.create_async(token)
    # Begin
    ls.progress.begin(
        token, WorkDoneProgressBegin(title="Indexing", percentage=0, cancellable=True)
    )
    # Report
    for i in range(1, 10):
        # Check for cancellation from client
        if ls.progress.tokens[token].cancelled():
            # ... and stop the computation if client cancelled
            return
        ls.progress.report(
            token,
            WorkDoneProgressReport(message=f"{i * 10}%", percentage=i * 10),
        )
        await asyncio.sleep(2)
    # End
    ls.progress.end(token, WorkDoneProgressEnd(message="Finished"))


@jaclang_server.command(JaclangLanguageServer.CMD_REGISTER_COMPLETIONS)
async def register_completions(ls: JaclangLanguageServer, *args):
    """Register completions method on the client."""
    params = RegistrationParams(
        registrations=[
            Registration(
                id=str(uuid.uuid4()),
                method=TEXT_DOCUMENT_COMPLETION,
                register_options={"triggerCharacters": "[':']"},
            )
        ]
    )
    response = await ls.register_capability_async(params)
    if response is None:
        ls.show_message("Successfully registered completions method")
    else:
        ls.show_message(
            "Error happened during completions registration.", MessageType.Error
        )


@jaclang_server.command(JaclangLanguageServer.CMD_SHOW_CONFIGURATION_ASYNC)
async def show_configuration_async(ls: JaclangLanguageServer, *args):
    """Gets exampleConfiguration from the client settings using coroutines."""
    try:
        config = await ls.get_configuration_async(
            WorkspaceConfigurationParams(
                items=[
                    ConfigurationItem(
                        scope_uri="",
                        section=JaclangLanguageServer.CONFIGURATION_SECTION,
                    )
                ]
            )
        )

        example_config = config[0].get("exampleConfiguration")

        ls.show_message(f"jsonServer.exampleConfiguration value: {example_config}")

    except Exception as e:
        ls.show_message_log(f"Error ocurred: {e}")


@jaclang_server.command(JaclangLanguageServer.CMD_SHOW_CONFIGURATION_CALLBACK)
def show_configuration_callback(ls: JaclangLanguageServer, *args):
    """Gets exampleConfiguration from the client settings using callback."""

    def _config_callback(config):
        try:
            example_config = config[0].get("exampleConfiguration")

            ls.show_message(f"jsonServer.exampleConfiguration value: {example_config}")

        except Exception as e:
            ls.show_message_log(f"Error ocurred: {e}")

    ls.get_configuration(
        WorkspaceConfigurationParams(
            items=[
                ConfigurationItem(
                    scope_uri="", section=JaclangLanguageServer.CONFIGURATION_SECTION
                )
            ]
        ),
        _config_callback,
    )


@jaclang_server.thread()
@jaclang_server.command(JaclangLanguageServer.CMD_SHOW_CONFIGURATION_THREAD)
def show_configuration_thread(ls: JaclangLanguageServer, *args):
    """Gets exampleConfiguration from the client settings using thread pool."""
    try:
        config = ls.get_configuration(
            WorkspaceConfigurationParams(
                items=[
                    ConfigurationItem(
                        scope_uri="",
                        section=JaclangLanguageServer.CONFIGURATION_SECTION,
                    )
                ]
            )
        ).result(2)

        example_config = config[0].get("exampleConfiguration")

        ls.show_message(f"jsonServer.exampleConfiguration value: {example_config}")

    except Exception as e:
        ls.show_message_log(f"Error ocurred: {e}")


@jaclang_server.command(JaclangLanguageServer.CMD_UNREGISTER_COMPLETIONS)
async def unregister_completions(ls: JaclangLanguageServer, *args):
    """Unregister completions method on the client."""
    params = UnregistrationParams(
        unregisterations=[
            Unregistration(id=str(uuid.uuid4()), method=TEXT_DOCUMENT_COMPLETION)
        ]
    )
    response = await ls.unregister_capability_async(params)
    if response is None:
        ls.show_message("Successfully unregistered completions method")
    else:
        ls.show_message(
            "Error happened during completions unregistration.", MessageType.Error
        )
