if not exist .\sqlite3.exe (
    echo Voce precisa baixar o sqlite3.exe e coloca-lo nesta pasta.
    exit
)
pyinstaller --onedir --add-binary "sqlite3.exe;." --name="horseradish" --noconfirm main.py