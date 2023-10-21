import os
import threading

SERVER_CWD = os.getcwd()
CWD_LOCK = threading.Lock()
ERROR_CODE_BASE_URL = "INCLUDE ERROR CODE BASE URL HERE"
SEE_HREF_PREFIX = "See LINK"
SEE_PREFIX_LEN = len("See ")
NOTE_CODE = "note"
LINE_OFFSET = CHAR_OFFSET = 1
