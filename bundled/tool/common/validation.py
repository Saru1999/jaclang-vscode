from jaclang.jac.passes.transform import Alert
from jaclang.jac.parser import JacParser
from jaclang.jac.absyntree import SourceString
from jaclang.jac.passes.blue import pass_schedule

from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range
from pygls.server import LanguageServer


def jac_to_errors(
    file_path: str, source: str, base_dir: str = "", schedule=pass_schedule
) -> tuple[list[Alert], list[Alert]]:
    """
    Converts JAC source to errors if any

    Args:
        file_path (str): The path to the JAC file
        source (str): The JAC source code
        base_dir (str, optional): The base directory. Defaults to "".
        schedule (list, optional): The list of validation functions to run. Defaults to pass_schedule.

    Returns:
        tuple[list[Alert], list[Alert]]: A tuple of errors and warnings
    """
    source = SourceString(source)
    prse = JacParser(
        mod_path=file_path, input_ir=source, base_path=base_dir, prior=None
    )
    for i in schedule:
        prse = i(mod_path=file_path, input_ir=prse.ir, base_path=base_dir, prior=prse)
    return prse.errors_had, prse.warnings_had


def validate(ls: LanguageServer, params: any):
    """
    Validates a jac file and publishes any diagnostics found.

    Args:
        ls (LanguageServer): The LanguageServer instance.
        params (any): The parameters for the validation.

    Returns:
        list: A list of diagnostics found during validation.
    """
    ls.show_message_log("Validating jac file...")

    text_doc = ls.workspace.get_text_document(params.text_document.uri)
    source = text_doc.source
    doc_path = params.text_document.uri.replace("file://", "")
    diagnostics = _validate_jac(doc_path, source) if source else []
    ls.publish_diagnostics(text_doc.uri, diagnostics)
    return diagnostics


def _validate_jac(doc_path: str, source: str) -> list[Diagnostic]:
    """
    Validate a JAC file.

    Args:
        doc_path (str): The path to the JAC file.
        source (str): The source code of the JAC file.

    Returns:
        list[Diagnostic]: A list of diagnostics for the JAC file.
    """
    diagnostics = []
    errors, warnings = jac_to_errors(doc_path, source)
    for alert in errors + warnings:
        msg = alert.msg
        loc = alert.loc
        diagnostics.append(
            Diagnostic(
                range=Range(
                    start=Position(line=loc.first_line, character=loc.col_start),
                    end=Position(line=loc.last_line, character=loc.col_end),
                ),
                message=msg,
                severity=DiagnosticSeverity.Error
                if alert in errors
                else DiagnosticSeverity.Warning,
            )
        )
    return diagnostics
