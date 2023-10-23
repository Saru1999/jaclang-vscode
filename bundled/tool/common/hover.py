from lsprotocol.types import Position, Location, TextDocumentItem
from typing import Optional
from .symbols import Symbol


def is_contained(sym_location: Location, hover_position: Position) -> bool:
    """
    Returns True if the hover position is contained within the symbol location.

    :param sym_location: The location of the symbol being checked.
    :type sym_location: Location
    :param hover_position: The position of the hover being checked.
    :type hover_position: Position
    :return: True if the hover position is contained within the symbol location, False otherwise.
    :rtype: bool
    """
    return (
        sym_location.range.start.line <= hover_position.line
        and sym_location.range.end.line >= hover_position.line
        and sym_location.range.start.character <= hover_position.character
        and sym_location.range.end.character >= hover_position.character
    )


def get_symbol_at_pos(doc: TextDocumentItem, pos: Position) -> Optional[Symbol]:
    """
    Returns the symbol at the given position.

    :param doc: The document to check.
    :type doc: TextDocumentItem
    :param pos: The position to check.
    :type pos: Position
    :return: The symbol at the given position, or None if no symbol is found.
    :rtype: Optional[Symbol]
    """
    for sym in doc.symbols:
        if is_contained(sym.location, pos):
            return sym
    return None
