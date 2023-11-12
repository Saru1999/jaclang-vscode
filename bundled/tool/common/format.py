from jaclang.jac.passes.main import (
    JacFormatPass,
)
from jaclang.jac.transpiler import jac_file_to_pass
import tempfile


def format_jac(source: str) -> str:
    return source
    # format_pass_schedule = [JacFormatPass]
    # with tempfile.NamedTemporaryFile(suffix=".jac") as f:
    #     f.write(source.encode("utf-8"))
    #     f.flush()
    #     return jac_file_to_pass(
    #         f.name, target=JacFormatPass, schedule=format_pass_schedule
    #     ).ir.gen.jac
