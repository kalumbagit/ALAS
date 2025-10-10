from enum import Enum

class ResponseStatus(str,Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"