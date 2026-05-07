git clone https://github.com/LandryLT/AnkiEZVocabAdder.git
cd AnkiEZVocabAdder
python -m venv .venv
copy NUL vocab2add.txt
call .\.venv\Scripts\activate
pip install -r requirements.txt
playwright install
pause
del ..\installer.bat