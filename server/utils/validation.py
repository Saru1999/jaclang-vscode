from jaclang.jac.lexer import JacLexer
from jaclang.jac.parser import JacParser
from jaclang.jac.transform import TransformError

import re

from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range


def _validate(ls, params):
    ls.show_message_log("Validating jac file...")

    text_doc = ls.workspace.get_document(params.text_document.uri)
    source = text_doc.source
    doc_path = params.text_document.uri.replace("file://", "")
    diagnostics = _validate_jac(doc_path, source) if source else []
    ls.publish_diagnostics(text_doc.uri, diagnostics)


def _validate_jac(doc_path: str, source: str) -> list:
    """validate jac file"""
    diagnostics = []
    lex = JacLexer(mod_path="", input_ir=source).ir
    prse = JacParser(mod_path="", input_ir=lex)

    if prse.errors_had or prse.warnings_had:
        combined = prse.errors_had + prse.warnings_had
        for err in combined:
            line = int(re.findall(r"Line (\d+)", err)[0].replace("Line ", ""))
            msg = " ".join(err.split(",")[1:])
            diagnostics.append(
                Diagnostic(
                    range=Range(
                        start=Position(line=line - 1, character=0),
                        end=Position(line=line - 1, character=0),
                    ),
                    message=msg,
                    severity=DiagnosticSeverity.Error if err in prse.errors_had else DiagnosticSeverity.Warning,
                )
            )

    return diagnostics
