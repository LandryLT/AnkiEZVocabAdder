python --version 3>NUL
if errorlevel 1 goto errorNoPython
git --version
if errorlevel 1 goto errorNoGit

git clone https://github.com/LandryLT/AnkiEZVocabAdder.git
cd AnkiEZVocabAdder
mkdir .\caches
mkdir .\caches\jisho
mkdir .\caches\neocities
mkdir .\caches\audio
mkdir .\caches\audio\words
mkdir .\caches\audio\sentences
mkdir .\caches\images
mkdir .\caches\kanjis
python -m venv .venv
copy NUL vocab2add.txt
call .\.venv\Scripts\activate
pip install -r requirements.txt
playwright install
del ..\installer.bat
echo .
echo "All done..."
echo .
echo "Please see searchConfig.txt to configurate AnkiEZ"
echo "Add search terms in vocab2add.txt (one per line)"
echo "Then launch AnliEZVocabAdder.bat to get started !"
echo .
echo "Have fun, press Enter to continue"
goto:eof

:errorNoPython
echo.
echo Error^: Python not installed
pause
goto:eof

:errorNoGit
echo.
echo Error^: Git not installed
pause