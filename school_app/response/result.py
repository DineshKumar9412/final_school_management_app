# response/result.py
from typing import Dict, Any, Optional
from fastapi.responses import JSONResponse

class Result:
    def __init__(
        self,
        code: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.extra = extra or {}

    def http_response(self):
        return JSONResponse(
            status_code=self.code,
            content={
                "code": self.code,
                "message": self.message,
                "result": self.extra,
            },
        )
