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
        "label": "loop",
        "detail": "for loop",
        "documentation": "for loop in jac",
        "insert_text": "for ${1:item} in ${2:iterable}:\n    ${3:# body of the loop}",
    },
]

JAC_KW = {
    "node": {"insert_text": "node", "documentation": "node"},
    "walker": {"insert_text": "walker", "documentation": "walker"},
    "edge": {"insert_text": "edge", "documentation": "edge"},
    "architype": {"insert_text": "architype", "documentation": "architype"},
    "from": {"insert_text": "from", "documentation": "from"},
    "with": {"insert_text": "with", "documentation": "with"},
    "in": {"insert_text": "in", "documentation": "in"},
    "graph": {"insert_text": "graph", "documentation": "graph"},
    "report": {"insert_text": "report", "documentation": "report"},
    "disengage": {"insert_text": "disengage", "documentation": "disengage"},
    "take": {"insert_text": "take", "documentation": "take"},
    "include:jac": {"insert_text": "include:jac", "documentation": "Importing in JAC"},
    "import:py": {
        "insert_text": "import:py",
        "documentation": "Import Python libraries",
    },
}

PY_LIBS = [name for _, name, _ in pkgutil.iter_modules() if "_" not in name]
