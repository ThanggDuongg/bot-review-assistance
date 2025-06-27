import os

class Utils:
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

    @staticmethod
    def debug_print(*args, **kwargs):
        if Utils.DEBUG_MODE:
            print("[DEBUG]", *args, **kwargs) 