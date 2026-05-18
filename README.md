# Anki Extra-Zealous Vocab Adder
**AnkiEZVocabAdder** is a script to easily add vocabulary and kanji notes to your Anki deck as you encounter them during yout studies.
It scraps different internet resources such as [jisho.org](https://www.jisho.org), [sentencesearch.neocities.org](https://sentencesearch.neocities.org/) and [kanji.sljfaq.org](https://kanji.sljfaq.org/kanjivg.html) for data for new notes.

There are a couple files you need to know about in this project to be able to correctly use this program.

## 1 - **installer.bat** - getting started

### Only works on Windows for now.


1. Get the latest version of [Python](https://www.python.org/downloads/) and [Git](https://git-scm.com/install/windows). 
2. Launch [`installer.bat`](https://github.com/LandryLT/AnkiEZVocabAdder/blob/main/installer/installer.bat) (***Ctrl+Maj+S*** *on linked page to download file*)
3. In the newly created *AnkiEZVocabAdder* folder you will find the three next important files.

## 2 - **searchConfig.txt** - configurate stuff
In [this file](https://github.com/LandryLT/AnkiEZVocabAdder/blob/main/searchConfig.txt) you can configure:
 - how automatically the scripts performs scrapping data on the different previously mentionned ressources
 - how much data is kept
 - a few things about the generated Anki cards.

Sections starting by `#` are commented out, thus ignored by the script and are only there to inform the user.

Please note that values set to `NONE` will later be prompted during runtime.
Also note that accepted values are noted on top of every settable parameter.

### General
Set the number of results per block shown by the script while manually selecting results.

### Caching
If ever the scripts encounters an error or if the user quits using the `quit` command, searched data is cached and can be retrieved next time the script is run.

### Expression
Configure how the scrapper searches [jisho.org](https://www.jisho.org). 
Each search term can return anywhere between 0 and 20 results, you can decide which ones are kept based on their JLPT level tag or in which order they arrived based on relevance. 
Each result then has *n* number of meanings, that can be more or less relevant. You can in a similar manner configure how the scripts selects these meanings.

### Audio
Configure if and how you want to auto-download audio for words and sentences.

### Sentences
Configure how the scrapper searches [sentencesearch.neocities.org](https://sentencesearch.neocities.org/) for sentences where the word to ankify is used. You can filter out search results based on how many characters they contain. The automatic sentence selector can either try select sentences with an evenly increasing number of characters inside the set of results, or just choose completely at random. You can then review the selected sentences, or just let the script decide.

### Anki
In this section, you can select on which collection you want to add new notes, choose how the scripts attempts to resolve card duplicates and a few extra things on how the cards are displayed in the app (stuff like how much time a hint takes to appear, or how many meanings, sentences, etc, are displayed)

## 3 - **vocab2add.txt** - list words to add
This file is where you list the terms to search :
```filename="vocab2add.txt"
毎日
かんじ
manabu
```

## 4 - **AnkiEZVocabAdder.bat** - scrap it
With everything ready, you can launch *AnkiEZVocabAdder.bat*, lay back, relax and let your brand new cards get generated for you.
