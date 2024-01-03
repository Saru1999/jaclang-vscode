from jaclang.compiler.passes.tool import (
    FuseCommentsPass,
    JacFormatPass,
)
from jaclang.compiler.transpiler import jac_str_to_pass


def format_jac(source: str) -> str:
    try:
        return jac_str_to_pass(
            jac_str=source,
            file_path="",
            target=JacFormatPass,
            schedule=[FuseCommentsPass, JacFormatPass],
        ).ir.gen.jac
    except Exception:
        return source
