from pygls.server import LanguageServer
import lsprotocol.types as lsp
import os


def log_to_output(
    ls: LanguageServer, message: str, msg_type: lsp.MessageType = lsp.MessageType.Log
) -> None:
    ls.show_message_log(message, msg_type)


def log_error(ls: LanguageServer, message: str) -> None:
    ls.show_message_log(message, lsp.MessageType.Error)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["onError", "onWarning", "always"]:
        ls.show_message(message, lsp.MessageType.Error)


def log_warning(ls: LanguageServer, message: str) -> None:
    ls.show_message_log(message, lsp.MessageType.Warning)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["onWarning", "always"]:
        ls.show_message(message, lsp.MessageType.Warning)


def log_always(ls: LanguageServer, message: str) -> None:
    ls.show_message_log(message, lsp.MessageType.Info)
    if os.getenv("LS_SHOW_NOTIFICATION", "off") in ["always"]:
        ls.show_message(message, lsp.MessageType.Info)
