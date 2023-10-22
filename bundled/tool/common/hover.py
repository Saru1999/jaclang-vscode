from lsprotocol.types import Position, Location


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
