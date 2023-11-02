import os
import threading
import pkgutil

SERVER_CWD = os.getcwd()
CWD_LOCK = threading.Lock()
ERROR_CODE_BASE_URL = "INCLUDE ERROR CODE BASE URL HERE"
SEE_HREF_PREFIX = "See LINK"
SEE_PREFIX_LEN = len("See ")
NOTE_CODE = "note"
LINE_OFFSET = CHAR_OFFSET = 1

SNIPPETS = [
    {
        "label": "for loop",
        "detail": "for loop",
        "documentation": "for loop in jac",
        "insert_text": "for ${1:item} in ${2:iterable}:\n    ${3:# body of the loop}",
        "positions": ["inside"],
    },
    {
        "label": "if statement",
        "detail": "if statement",
        "documentation": "if statement in jac",
        "insert_text": "if ${1:condition}{\n    ${2:# body of the if statement}\n}",
        "positions": ["inside"],
    },

]

JAC_KW = {
    "node": {"insert_text": "node", "documentation": "node", "positions": ["at_start"]},
    "walker": {
        "insert_text": "walker",
        "documentation": "walker",
        "positions": ["at_start"],
    },
    "edge": {"insert_text": "edge", "documentation": "edge", "positions": ["at_start"]},
    "object": {
        "insert_text": "object",
        "documentation": "object",
        "positions": ["at_start"],
    },
    "include:jac": {
        "insert_text": "include:jac",
        "documentation": "Importing in JAC",
        "positions": ["at_start"],
    },
    "import:py": {
        "insert_text": "import:py",
        "documentation": "Import Python libraries",
        "positions": ["at_start"],
    },
    "import:py from": {
        "insert_text": "import:py from",
        "documentation": "Import Python libraries",
        "positions": ["at_start"],
    },
    "enum": {
        "insert_text": "enum",
        "documentation": "enum",
        "positions": ["at_start"],
    },
    "can": {"insert_text": "can", "documentation": "can", "positions": ["at_start", "inside"]},
    "test": {"insert_text": "test", "documentation": "test", "positions": ["at_start"]},
    "with entry": {
        "insert_text": "with entry",
        "documentation": "with entry",
        "positions": ["at_start"],
    },
    "global": {
        "insert_text": "global",
        "documentation": "global",
        "positions": ["at_start", "inside"],
    },
    "<self>": {
        "insert_text": "<self>",
        "documentation": "self",
        "positions": ["inside"],
    },
    "visit": {
        "insert_text": "visit",
        "documentation": "visit",
        "positions": ["inside"],
    },
    "disengage": {
        "insert_text": "disengage",
        "documentation": "disengage",
        "positions": ["inside"],
    },
    "<root>": {
        "insert_text": "<root>",
        "documentation": "root",
        "positions": ["inside"],
    },
    "can": {
        "insert_text": "can",
        "documentation": "can",
        "positions": ["inside"],
    },
    "with": {
        "insert_text": "with",
        "documentation": "with",
        "positions": ["inside"],
    }
}

PY_LIBS = [name for _, name, _ in pkgutil.iter_modules() if "_" not in name]
