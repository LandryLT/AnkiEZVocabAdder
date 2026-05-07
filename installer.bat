git clone https://github.com/LandryLT/AnkiEZVocabAdder.git
cd AnkiEZVocabAdder
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
playwright install
copy NUL vocab2add.txt
del ..\installer.bat
pause