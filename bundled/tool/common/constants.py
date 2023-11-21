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

SEMANTIC_TOKEN_TYPES = [
    "type",  # 0
    "class",  # 1
    "enum",  # 2
    "interface",  # 3
    "struct",  # 4
    "typeParameter",  # 5
    "parameter",  # 6
    "variable",  # 7
    "property",  # 8
    "enumMember",  # 9
    "event",  # 10
    "function",  # 11
    "method",  # 12
    "macro",  # 13
    "keyword",  # 14
    "modifier",  # 15
    "comment",  # 16
    "string",  # 17
    "number",  # 18
    "regexp",  # 19
    "operator",  # 20
    "decorator",  # 21
]

SEMANTIC_TOKEN_MODIFIERS = [
    "declaration",  # 0
    "definition",  # 1
    "readonly",  # 2
    "static",  # 3
    "deprecated",  # 4
    "abstract",  # 5
    "async",  # 6
    "modification",  # 7
    "documentation",  # 8
    "defaultLibrary",  # 9
]

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

WALKER_SNIPPET = [
    {
        "label": "Has Variable",
        "detail": "has {var_name}: {var_type} ...;",
        "documentation": "Adds a variable to the walker.",
        "insert_text": "has ${1:var_name}: ${2:var_type};",
    },
    {
        "label": "Ability without arguments",
        "detail": "can {ability_name} {...}",
        "documentation": "Adds an ability to the walker.",
        "insert_text": "can ${1:ability_name} {\n    ${2:# body of the ability}\n}",
    },
    {
        "label": "Ability with arguments",
        "detail": "can {ability_name}( {var_name}: {var_type} )",
        "documentation": "Adds an ability to the walker.",
        "insert_text": "can ${1:ability_name}( ${2:var_name}: ${3:var_type} ) {\n    ${4:# body of the ability}\n}",
    },
    {
        "label": "Entry",
        "detail": "with entry {...}",
        "documentation": "Defines what happens when the walker enters a node.",
        "insert_text": "with entry {\n    ${1:# body of the entry}\n}",
    },
    {
        "label": "Exit",
        "detail": "with exit {...}",
        "documentation": "Defines what happens when the walker exits a node.",
        "insert_text": "with exit {\n    ${1:# body of the exit}\n}",
    },
]

ENUM_SNIPPETS = [
    {
        "label": "Enum Key Value",
        "detail": "{enum_key} = {enum_value}",
        "documentation": "Enum Key",
        "insert_text": "${1:enum_key} = ${2:enum_value},",
    },
]


NODE_SNIPPET = [
    {
        "label": "Has Variable",
        "detail": "has {var_name}: {var_type} ...;",
        "documentation": "Adds a variable to the node.",
        "insert_text": "has ${1:var_name}: ${2:var_type};",
    },
    {
        "label": "Ability without arguments",
        "detail": "can {ability_name} {...}",
        "documentation": "Adds an ability to the node.",
        "insert_text": "can ${1:ability_name} {\n    ${2:# body of the ability}\n}",
    },
    {
        "label": "Ability with arguments",
        "detail": "can {ability_name}( {var_name}: {var_type} )",
        "documentation": "Adds an ability to the node.",
        "insert_text": "can ${1:ability_name}( ${2:var_name}: ${3:var_type} ) {\n    ${4:# body of the ability}\n}",
    },
    {
        "label": "Entry",
        "detail": "with entry {...}",
        "documentation": "Defines what happens when the walker enters a node.",
        "insert_text": "with entry {\n    ${1:# body of the entry}\n}",
    },
    {
        "label": "Exit",
        "detail": "with exit {...}",
        "documentation": "Defines what happens when the walker exits a node.",
        "insert_text": "with exit {\n    ${1:# body of the exit}\n}",
    },
]

ABILITY_SNIPPETS = [] #TODO: Add ability snippets


OBJECT_SNIPPETS = [
    {
        "label": "Constructor",
        "detail": "can <init>",
        "documentation": "Constructor",
        "insert_text": "can <init> {\n    ${1:# body of the constructor}\n}",
    },
    {
        "label": "Ability without arguments",
        "detail": "can {ability_name} -> {return_type}",
        "documentation": "Ability",
        "insert_text": "can ${1:ability_name} -> ${2:return_type} {\n    ${3:# body of the ability}\n}",
    },
    {
        "label": "Ability with arguments",
        "detail": "can {ability_name}( {var_name}: {var_type} ) -> {return_type}",
        "documentation": "Ability",
        "insert_text": "can ${1:ability_name}( ${2:var_name}: ${3:var_type} ) -> ${4:return_type} {\n    ${5:# body of the ability}\n}",
    },
    {
        "label": "Has Variable",
        "detail": "has {var_name}: {var_type} ...;",
        "documentation": "Adds a variable to the object.",
        "insert_text": "has ${1:var_name}: ${2:var_type};",
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
    "can": {
        "insert_text": "can",
        "documentation": "can",
        "positions": ["at_start", "inside"],
    },
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
    "with": {
        "insert_text": "with",
        "documentation": "with",
        "positions": ["inside"],
    },
}

PY_LIBS = [name for _, name, _ in pkgutil.iter_modules() if "_" not in name]
