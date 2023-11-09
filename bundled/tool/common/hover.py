from typing import Optional

from lsprotocol.types import (
    Position,
    TextDocumentItem,
    Hover,
    MarkupContent,
    MarkupKind,
)
from pygls.server import LanguageServer

from .symbols import Symbol
from .utils import get_symbol_at_pos


def get_hover_info(ls: LanguageServer, doc: TextDocumentItem, pos: Position) -> Optional[Hover]:
    """
    Returns the hover information for the symbol at the given position.

    :param doc: The document to check.
    :type doc: TextDocumentItem
    :param pos: The position to check.
    :type pos: Position
    :return: The hover information for the symbol at the given position, or None if no symbol is found.
    :rtype: Optional[Hover]
    """
    symbol: Symbol = get_symbol_at_pos(ls, doc, pos)
    if symbol is not None:
        return Hover(
            contents=MarkupContent(
                kind=MarkupKind.PlainText,
                value="\n".join(
                    [f"({symbol.sym_type}) {symbol.sym_name}", symbol.sym_doc]
                ),
            ),
            range=symbol.location.range,
        )
    return None
