from fastapi import HTTPException

def handle_error(e: Exception, status_code: int = 400):
    return HTTPException(status_code=status_code, detail=str(e))
