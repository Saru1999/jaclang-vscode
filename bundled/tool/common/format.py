from jaclang.jac.passes.blue import (
    JacFormatPass,
)
from jaclang.jac.transpiler import jac_file_to_pass


def format_jac(doc_uri: str) -> str:
    format_pass_schedule = [JacFormatPass]
    doc_url = doc_uri.replace("file://", "")
    prse = jac_file_to_pass(
        doc_url, target=JacFormatPass, schedule=format_pass_schedule
    )
    return prse.ir.gen.jac
