from scripts.utils.printingUtils import bold, italic, grey, clearConsole, tqdm_bar_format
from enum import Enum
from scripts.scrappers.JishoSearchResult import JishoResult, JishoSearchResultRaw
from scripts.scrappers.Scrapper import Scrapper, oopsable
import re
from tqdm.asyncio import tqdm

class JishoScrapper(Scrapper):
    class SelectMode(Enum):
        NONE = -1
        FIRST = 0
        SELECT = 1
        ALL = 2
    
    def __init__(self, page, max_rez_display):
        super().__init__(page, max_rez_display)

    @oopsable()
    async def selectExpressions(self, vocab_list: list[str], mode: SelectMode = None, is_exact_match_autoselect: bool = False) -> list[JishoResult]:
        # Auto-select expression mode
        clearConsole()
        while mode == self.SelectMode.NONE:
            clearConsole()
            print(grey("Auto-select \033[1mexpression\033[0m\033[2m mode"))
            print(f"\t{bold('1')}. First only")
            print(f"\t{bold('2')}. Select")
            print(f"\t{bold('3')}. All")
            response = re.match(r'([1-3]|oops)', self._checkAbortResponse(f'{grey("Select mode")} ({bold("1")}|{bold("2")}|{bold("3")}) {grey(": ")}'))
            if response:
                mode = self.SelectMode(int(response.group(0))-1)
                self.logger.info(f"Auto-selecting expression mode is {mode.name}")
            # Auto-select exact match
            if mode == self.SelectMode.SELECT:
                response = self._checkAbortResponse(f"\n{grey('Enable auto-selecting only exact matches ?')} ({bold('y')}|{bold('n')}) {grey(':')} ")
                is_exact_match_autoselect = re.match(r'(?i:^y(es)?$)', response) != None
                self.logger.info(f"Auto-selecting exact matches is {'en' if is_exact_match_autoselect else 'dis'}abled")
        
        output = []
        expression_question = True
        # Go through vocab list
        for word_ind, word in enumerate(vocab_list):
            word = word.replace('\r\n', "")
            header = f'[{bold(word)}] {grey(f"({word_ind + 1}/{len(vocab_list)} search terms)")}\n'
            jisho_results = await self.jishoSearchTerm(word, header)
            clearConsole()
            print(f'[{bold(word)}] {grey(f"({word_ind + 1}/{len(vocab_list)} search terms)")}\n')
            
            # No results
            if not jisho_results:
                continue
            # Exact match and auto-select
            if mode == self.SelectMode.FIRST or (mode == self.SelectMode.SELECT and is_exact_match_autoselect and jisho_results[0].is_exact_match) or len(jisho_results) == 1:
                if jisho_results[0].is_exact_match:
                    self.logger.warning(f"Found exact match for {word} !")
                output.append(jisho_results[0])
                continue
            elif mode == self.SelectMode.ALL:
                [output.append(rez) for rez in jisho_results]
                continue

            self.promptForSelection(choices=[f"{bold(expr.expression)} ({expr.romaji}):\t\"{italic(expr.meanings[0].meaning)}\" {grey(f'(1/{len(expr.meanings)} meanings)')}" for expr in jisho_results], 
                                    input_text=(grey("Expressions indices to keep ") + f"({grey('ex:')} {bold('0, 2, 7')} {grey('or')} {bold('a')} {grey('or')} {bold('none')}) " if expression_question else "") + ": ",
                                    header=header+grey(f"\nPlease select expressions to keep"),
                                    callback=lambda i: output.append(jisho_results[i]))
            
            expression_question = False
        return output
    
    @oopsable()
    async def downloadSounds(self, selected_expr: list[JishoResult], enable:bool = True, auto_download: bool = None) -> list[JishoResult]:
        output = selected_expr.copy()
        expr_with_links = [expr for expr in output if expr.soundlink]
        if not enable:
            return output
        clearConsole()
        if not expr_with_links:
            self.logger.info("No soundlinks found in selected expressions, skipping...")
            return output
        if auto_download == None:
            auto_download = re.match(r'(?i:^y(es)?$)', self._checkAbortResponse(grey('\033[1mAuto-download sound\033[0m\033[2m when found ?') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None
            self.logger.info(f"Auto-downloading sound is {'en' if auto_download else 'dis'}abled")
        
        if auto_download:
            print(grey(italic(f'Downloading {len(expr_with_links)} audio files...\n')))
            download_cors = [e.downloadSound() for e in expr_with_links]
            await tqdm.gather(*download_cors, bar_format=tqdm_bar_format)
            return output
        
        for i, expression in enumerate(expr_with_links):
            clearConsole()
            print(f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(expr_with_links)} sounds to download)")}\n')
            if re.match(r'(?i:^y(es)?$)', self._checkAbortResponse(grey('Skip this file ? ') + f"({bold('y')}|{bold('n')}) {grey(':')} ")) != None:
                continue
            clearConsole()
            print(f'[{expression.search_term} - {bold(expression.expression)}] {grey(f"({i + 1}/{len(expr_with_links)} sounds to download)")}\n')
            print(italic(grey(f'Downloading audio from jisho.org')))
            await expression.downloadSound()
        return output
        
    @oopsable()
    async def selectMeanings(self, selected_expr: list[JishoResult], mode: SelectMode = SelectMode.NONE) -> list[JishoResult]:
        # Auto-select meanings mode
        while mode == self.SelectMode.NONE:
            clearConsole()
            print(grey("Auto-select \033[1mmeaning\033[0m\033[2m mode"))
            print(f"\t{bold('1')}. First only")
            print(f"\t{bold('2')}. Select")
            print(f"\t{bold('3')}. All")
            response = re.match(r'[1-3]', self._checkAbortResponse(f'{grey("Select mode")} ({bold("1")}|{bold("2")}|{bold("3")}) {grey(": ")}'))
            if response:
                mode = self.SelectMode(int(response.group(0))-1)
                self.logger.info(f"Auto-selecting definition mode is {mode.name}")

        
        output = selected_expr.copy()
        expression_question = True
        for i, expression in enumerate(output):
            clearConsole()
            print(f'[{expression.search_term} - {bold(expression.expression)} ({expression.furigana})] {grey(f"({i + 1}/{len(output)} search terms)")}\n')
            if mode == self.SelectMode.SELECT and len(expression.meanings) > 1:
                selected_def = []
                self.promptForSelection(choices=[f"{italic(m.meaning)}" for m in expression.meanings], 
                                        input_text=(grey("Meanings indices to keep ") + f"({grey('ex:')} {bold('0, 2, 7')} {grey('or')} {bold('a')}) " if expression_question else "") + ": ",
                                        header=f'[{expression.search_term} - {bold(expression.expression)} ({expression.furigana})] {grey(f"({i + 1}/{len(output)} expressions to check)")}\n'+
                                                    grey(f"\nPlease select meanings to keep"),
                                        callback=lambda i: selected_def.append(expression.meanings[i]),
                                        use_none=False)
                expression_question = False
                expression.meanings = selected_def

            elif mode == self.SelectMode.FIRST:

                expression.meanings = [expression.meanings[0]]

            self.logger.debug(f"{[{expression.search_term} - {bold(expression.expression)}]}'s meanings: {expression.meanings}")
        return output
    
    async def jishoSearchTerm(self, search_term: str, header: str) -> list[JishoResult]:
        clearConsole()
        print(header)
        print(italic(grey(f'Loading from jisho.org...\n')))
        await self.page.goto(self._jishosearch(search_term))
        dict_rez = await self.page.evaluate("""() => {
                                                function getDomPath(el) {
                                                    if (!(el instanceof Element)) return null;
                                                    const path = [];
                                                    while (el && el.nodeType === Node.ELEMENT_NODE) {
                                                        let selector = el.nodeName.toLowerCase();

                                                        // Prefer ID if available
                                                        if (el.id) {
                                                        selector += `#${CSS.escape(el.id)}`;
                                                        path.unshift(selector);
                                                        break;
                                                        }

                                                        // Add classes
                                                        if (el.classList.length) {
                                                        selector += [...el.classList]
                                                            .map(cls => `.${CSS.escape(cls)}`)
                                                            .join('');
                                                        }

                                                        // Add nth-of-type for uniqueness
                                                        let sibling = el;
                                                        let nth = 1;

                                                        while ((sibling = sibling.previousElementSibling)) {
                                                        if (sibling.nodeName === el.nodeName) nth++;
                                                        }

                                                        selector += `:nth-of-type(${nth})`;

                                                        path.unshift(selector);
                                                        el = el.parentElement;
                                                    }

                                                    return path.join(' > ');
                                                }
                                                return [...document.querySelectorAll('#primary > div > div')].map((el) => ({
                                                    expression: el.querySelector('.text')?.innerText ?? '',
                                                    furiganas: [...el.querySelectorAll('.furigana .kanji')].map(x => x.innerText),
                                                    meanings: (() => {
                                                        const m = el.querySelector('.concept_light-meanings > .meanings-wrapper')
                                                        const tags = [...m.querySelectorAll('.meaning-tags')].map(x => x.innerText)
                                                        const meanings = [...m.querySelectorAll('.meaning-meaning')].map(x => x.innerText)
                                                        const supplemental_infos = [...m.querySelectorAll('.meaning-wrapper')].map(x => [...x.querySelectorAll('.supplemental_info > span.tag-tag')].map(y => y.innerText))
                                                        const output = meanings.map((x, i) => ({
                                                            tag: tags[i],
                                                            meaning: meanings[i],
                                                            supplemental_info: supplemental_infos[i],
                                                        }))
                                                        return output.filter(x => (x["tag"] != "Notes" && x["tag"] != "Other forms"))
                                                    })(),
                                                    tags: [...el.querySelectorAll('.concept_light-tag')].map(x => x.innerText),
                                                    soundlink: el.querySelector('source[type="audio/mpeg"]')?.src ?? null,
                                                    inflectionlink: getDomPath(el.querySelector('.show_inflection_table')) ?? null
                                                }))
                                            }""")
        output = [JishoResult(JishoSearchResultRaw(**rez), search_term) for rez in dict_rez]
        [await rez.queryInflection(self.page) for rez in output]
        return output
    
    @staticmethod
    def _jishosearch(term: str) -> str:
        return f'https://jisho.org/search/{term}'
