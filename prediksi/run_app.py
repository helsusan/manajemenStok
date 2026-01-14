import sys
import os
from streamlit.web import cli as stcli

def resolve_path(path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)

if __name__ == "__main__":
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("app.py"), # Arahkan ke file utama Anda
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())