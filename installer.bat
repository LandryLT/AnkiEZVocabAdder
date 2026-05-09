git clone https://github.com/LandryLT/AnkiEZVocabAdder.git
cd AnkiEZVocabAdder
mkdir .\audio
mkdir .\audio\words
mkdir .\audio\sentences
python -m venv .venv
copy NUL vocab2add.txt
call .\.venv\Scripts\activate
pip install -r requirements.txt
playwright install
pause
@REM mklink /h .\AnkiEZVocabAdder ..\AnkiEZVocabAdder.bat
@REM mklink /h .\vocab_to_add.txt ..\vocab_to_add.txt
del ..\installer.bat