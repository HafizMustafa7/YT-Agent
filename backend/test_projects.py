import asyncio
from app.services.video_service import get_user_projects
import logging

logging.basicConfig(level=logging.DEBUG)

def test():
    # Provide a real user_id from the database to test
    # Or just run it with a dummy one
    try:
        res = get_user_projects("2b874cb8-abde-48a0-97eb-2a316dfa3c10")
        print("Success:", res)
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    test()
