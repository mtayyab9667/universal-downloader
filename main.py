import sys
import os

# Ensure local directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import UniversalDownloaderApp

def main():
    app = UniversalDownloaderApp()
    app.mainloop()

if __name__ == "__main__":
    main()
