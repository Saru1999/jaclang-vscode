from jaclang.jac.passes.transform import Alert
from jaclang.jac.parser import JacParser
from jaclang.jac.absyntree import JacSource
from jaclang.jac.passes.blue import pass_schedule

from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range
from pygls.server import LanguageServer


def jac_to_errors(
    file_path: str, source: str, schedule=pass_schedule
) -> tuple[list[Alert], list[Alert]]:
    source = JacSource(source, file_path)
    prse = JacParser(source)
    for i in schedule:
        prse = i(input_ir=prse.ir, prior=prse)
    return prse.errors_had, prse.warnings_had


def validate(
    ls: LanguageServer, params: any, use_source: bool = False, rebuild: bool = False
) -> list[Diagnostic]:
    text_doc = ls.workspace.get_text_document(params.text_document.uri)
    source = text_doc.source
    doc_path = params.text_document.uri.replace("file://", "")
    diagnostics = (
        _validate_jac(ls, doc_path, source, use_source, rebuild) if source else []
    )
    ls.publish_diagnostics(text_doc.uri, diagnostics)
    return diagnostics


def _validate_jac(
    ls: LanguageServer,
    doc_path: str,
    source: str,
    use_source: bool = False,
    rebuild: bool = False,
) -> list[Diagnostic]:
    """
    Validate a JAC file.

    Args:
        doc_path (str): The path to the JAC file.
        source (str): The source code of the JAC file.
        use_source (bool, optional): Whether to use the source code to validate the JAC file. Defaults to False.
        rebuild (bool, optional): Whether to rebuild the JAC file. Defaults to False.

    Returns:
        list[Diagnostic]: A list of diagnostics for the JAC file.
    """
    diagnostics = []
    if use_source:
        errors, warnings = jac_to_errors(doc_path, source)
    else:
        if rebuild:
            ls.jlws.rebuild_file(doc_path)
        errors, warnings = (
            ls.jlws.modules[doc_path].errors,
            ls.jlws.modules[doc_path].warnings,
        )
        warnings = warnings if ls.settings.get("showWarning") else []
    for alert in errors + warnings:
        msg = alert.msg
        loc = alert.loc
        diagnostics.append(
            Diagnostic(
                range=Range(
                    start=Position(
                        line=loc.first_line - 1, character=loc.col_start - 1
                    ),
                    end=Position(line=loc.last_line - 1, character=loc.col_end - 1),
                ),
                message=msg,
                severity=DiagnosticSeverity.Error
                if alert in errors
                else DiagnosticSeverity.Warning,
            )
        )
    return diagnostics
