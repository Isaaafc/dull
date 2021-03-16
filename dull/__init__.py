from pandas._config.config import options
from pandas.core.algorithms import SelectNSeries
from rich.live import Live
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from .utils import get_first_item
import pandas as pd
import click
import os
import re

__version__ = '0.1.0'

controls = ['w', 's', 'd', 'a']

instruction = """
a: previous token
d: next token
w: scroll up corpus
s: scroll down corpus
<numbers>: toggle tag
:q: quit
:e: save
:f: edit token
:<number>: go to token
"""

edit_token_instruction = """
--Edit token--

z: left expand
x: left shrink
c: right shrink
v: right expand
b: undo changes
<tab>: edit translation
<Enter>: save changes
"""

edit_translation_instruction = """
--Edit translation--

<char>: append char
<backspace>: remove char
<tab>: edit token
"""

def display_corpus(pos, token, corpus, selected=[], highlight_token=None):
    """
    Returns a panel with token as the title and corpus as the body

    Parameters
    ----------
    pos:
        Position of token
    token:
        Token to display
    corpus:
        List[str] of the section of corpus to display
    trim:
        Whether to trim the result to show only the section that contains the first occurence of the token
    selected:
        List[int] of indices representing the currently selected corpus
    highlight_token:
        Position of token to highlight
    """
    _tok = get_first_item(token)
    
    content = []

    for i, c in enumerate(corpus):
        c = c.replace(_tok, f'[yellow]{_tok}[/yellow]')

        if i in selected:
            c = '[bold magenta]>>[/bold magenta] ' + c
        elif len(selected) > 0:
            c = '   ' + c
        
        content.append(c)

    title = [Text(f'{pos}.')]

    for i, t in enumerate(token):
        st = Text.styled(t, Style(color='black', bgcolor='white')) if highlight_token is not None and i == highlight_token else Text(t)
        title.append(Text.assemble(' | ', st))

    title = Text.assemble(*title)
    
    return Panel('\n'.join(content), title=title)

def display_options(options, selected):
    grids = []

    for i, opt in enumerate(options):
        text = Text(f'{i + 1}. {opt}')

        if selected[opt]:
            text.stylize('yellow')
        
        grids.append(Layout(text))

    layout = Layout(name='options')
    layout.split(*grids, direction='horizontal')

    return layout

# TODO create another class to separate display state

class UI():
    def __init__(self, corpus_path, tokens_path, save_config, options, tokens_cols, display_range=20, corpus_col_name='short_event_description', tokenized_col_name='preprocessed_tokens', filter_na_cols=None):
        self.data = pd.read_csv(corpus_path)
        self.tokenized_col_name = tokenized_col_name
        self.corpus_col_name = corpus_col_name

        self.tokens = pd.read_csv(tokens_path)

        if filter_na_cols is not None and len(filter_na_cols) > 0:
            self.tokens = self.tokens.dropna(subset=filter_na_cols)

        self.tokens_cols = tokens_cols

        savedir = save_config['save_dir']

        if not os.path.exists(savedir):
            os.mkdir(savedir)

        self.tokens_save_path = os.path.join(savedir, save_config['save_file_name'])
        self.tokens_backup_path = os.path.join(savedir, save_config['backup_file_name'])
        self.corpus_save_path = os.path.join(savedir, 'corpus.csv')
        self.corpus_backup_path = os.path.join(savedir, 'corpus_backup.csv')

        self.options = options
        self.display_range = display_range
        
        for opt in options:
            if opt not in self.tokens.columns:
                self.tokens[opt] = None

        self.goto_token(0)

        self.live = None
        self.msg = ''
    
    def start(self):
        with Live(self.get_grid(), auto_refresh=False, transient=True) as live:
            while True:
                self.display_state.instruction = instruction
                live.update(self.get_grid(), refresh=True)

                c = click.getchar()

                if not (len(self.msg) > 0 and self.msg[0] == ':') and c in controls + [str(i + 1) for i in range(len(self.options))]:
                    if c == 'a':
                        self.update_option()
                        self.goto_token((self.token_pos - 1) % len(self.tokens))
                    elif c == 'd':
                        self.update_option()
                        self.goto_token((self.token_pos + 1) % len(self.tokens))
                    elif c == 'w':
                        self.display_state.scroll_up()
                    elif c == 's':
                        self.display_state.scroll_down()
                    else:
                        self.selected[self.options[int(c) - 1]] = not self.selected[self.options[int(c) - 1]]
                elif c == ':':
                    self.msg = ':'
                elif self.msg[0] == ':':
                    if c == 'q':
                        # Save to backup and quit
                        self.msg = ':q\nExiting'

                        try:
                            self.save_token(self.tokens_backup_path)
                            self.save_corpus(self.corpus_backup_path)
                            live.update(self.get_grid(), refresh=True)
                            exit(0)
                        except PermissionError:
                            self.msg = 'Save failed. Check if the file is opened in another program.'
                            live.update(self.get_grid(), refresh=True)
                    elif c == 'e':
                        # Save to save file
                        self.update_option()

                        try:
                            self.msg = f':e\nSaving'
                            self.save_token(self.tokens_save_path)
                            self.save_corpus(self.corpus_save_path)
                            self.msg = 'Saved'
                        except:
                            self.msg = 'Save failed. Check if the file is opened in another program.'
                            live.update(self.get_grid(), refresh=True)
                    elif c == 'f':
                        # Edit token
                        self.edit_token(live)
                    elif c in '0123456789':
                        self.msg = self.msg + c

                        pos = int(self.msg[1:])
                        
                        if pos < len(self.tokens):
                            self.update_option()
                            self.goto_token(int(self.msg[1:]))
                        else:
                            self.msg = ''
                    else:
                        self.msg = 'Invalid command'

    def current_token(self):
        return self.tokens.iloc[self.token_pos][self.tokens_cols[0]]

    def goto_token(self, pos):
        self.token_pos = pos

        current_corpus = self.data.loc[self.data[self.tokenized_col_name] == self.current_token()][self.corpus_col_name].unique()

        self.display_state = DisplayState(
            corpus=current_corpus,
            token=[s for s in self.tokens.iloc[pos][self.tokens_cols]],
            display_range=self.display_range,
            corpus_pos=0
        )

        r = self.tokens.iloc[pos][self.options]
        self.selected = {opt: r[opt] == 'y' for opt in self.options}

    def update_option(self):
        for opt in self.selected:
            self.tokens.iloc[self.token_pos, self.tokens.columns.get_loc(opt)] = 'y' if self.selected[opt] else None

    def edit_token(self, live):
        self.display_state.current_selection_pos = 0

        while True:
            self.msg = 'Edit token'
            self.display_state.highlight_token = 0
            self.display_state.instruction = edit_token_instruction

            live.update(self.get_grid(), refresh=True)
            
            c = click.getchar()

            if c == 'w':
                self.display_state.scroll_up_selection()
            elif c == 's':
                self.display_state.scroll_down_selection()
            elif c == 'z':
                self.display_state.left_expand_token()
            elif c == 'x':
                self.display_state.left_shrink_token()
            elif c == 'c':
                self.display_state.right_shrink_token()
            elif c == 'v':
                self.display_state.right_expand_token()
            elif c == 'b':
                # Restore token
                self.display_state.token = [s for s in self.tokens.iloc[self.token_pos][self.tokens_cols]]
            elif c == '\t':
                # Edit translation
                self.edit_translation(live)
            elif c == '\r':
                # Save token and quit
                self.display_state.current_selection_pos = None
                self.display_state.highlight_token = None

                # Edit the token in the corpus
                old_token, new_token = self.current_token(), get_first_item(self.display_state.token)
                filt = (self.data[self.tokenized_col_name] == old_token) & (self.data[self.corpus_col_name].str.contains(new_token))
                
                self.data.loc[filt, self.tokens_cols[0]] = get_first_item(self.display_state.token)
                self.data.loc[filt, self.tokens_cols[1]] = self.display_state.token[1]
                
                for i, tc in enumerate(self.tokens_cols):
                    self.tokens.iloc[self.token_pos, self.tokens.columns.get_loc(tc)] = self.display_state.token[i]

                self.msg = ''
        
                break

    def edit_translation(self, live):
        translation = self.tokens.iloc[self.token_pos][self.tokens_cols[1]]

        while True:
            self.msg = f'Editing translation: {translation}'
            self.display_state.token[1] = translation
            self.display_state.highlight_token = 1
            self.display_state.instruction = edit_translation_instruction
            
            live.update(self.get_grid(), refresh=True)

            c = click.getchar()

            if c == '\t':
                self.msg = f'Edit token'
                live.update(self.get_grid(), refresh=True)
                return
            elif re.match(r'[a-zA-Z0-9\s\-]', c):
                translation = translation + c
            elif c in ['\x7f', '\x08']:
                if len(translation) > 0:
                    translation = translation[:-1]
            
    def get_grid(self):
        layout = Layout()

        upper = Layout()
        upper.split(
            Layout(display_corpus(self.token_pos, self.display_state.token, self.display_state.current_corpus(), selected=self.display_state.get_selected_pos(), highlight_token=self.display_state.highlight_token), name='panel', ratio=4),
            Layout(Panel(self.display_state.instruction, title='Controls', expand=False), name='instruction', ratio=1),
            direction='horizontal'
        )

        lower = Layout()
        lower.split(
            Layout(display_options(self.options, self.selected), ratio=4),
            Layout(Panel(self.msg, title='Command', height=5), name='cmd', ratio=1),
            direction='horizontal'
        )

        layout.split(upper, lower)

        return layout

    def save_token(self, save_path):
        self.tokens.to_csv(save_path, index=False, encoding='utf-8')
    
    def save_corpus(self, save_path):
        self.data.to_csv(save_path, index=False, encoding='utf-8')

class DisplayState():
    """
    Represents the display state for a *single* token
    """
    def __init__(self, corpus, token, display_range, corpus_pos=0, instruction=instruction):
        self.corpus = corpus
        self.token = token
        self.display_range = display_range
        self.corpus_pos = corpus_pos
        self.current_selection_pos = None
        self.highlight_token = None
        self.instruction = instruction

    def scroll_down(self):
        self.corpus_pos = min(len(self.corpus) - self.display_range, self.corpus_pos + self.display_range)
    
    def scroll_up(self):
        self.corpus_pos = max(0, self.corpus_pos - self.display_range)

    def current_corpus(self):
        return self.corpus[self.corpus_pos:self.corpus_pos + self.display_range]

    def scroll_down_selection(self):
        if self.current_selection_pos == self.display_range - 1 and self.corpus_pos >= len(self.corpus) - self.display_range:
            # Bottom
            return

        self.current_selection_pos = self.current_selection_pos + 1 if self.current_selection_pos is not None else 0

        if self.current_selection_pos >= self.display_range:
            self.current_selection_pos = 0
            self.scroll_down()

    def scroll_up_selection(self):
        if self.current_selection_pos == 0 and self.corpus_pos == 0:
            # Top
            return

        self.current_selection_pos = self.current_selection_pos - 1 if self.current_selection_pos is not None else 0

        if self.current_selection_pos < 0:
            self.current_selection_pos = self.display_range - 1
            self.scroll_up()

    def update_token(self, token):
        self.token[0] = token

    def left_expand_token(self):
        """
        Expand the token by 1 character to the left of the current selected corpus
        """
        current_corpus = self.current_corpus()[self.current_selection_pos]
        token = get_first_item(self.token)

        s = current_corpus.find(token)

        if s > 0:
            self.update_token(current_corpus[s - 1:s + len(token)])
        
    def right_expand_token(self):
        """
        Expand the token by 1 character to the right of the current selected corpus
        """
        current_corpus = self.current_corpus()[self.current_selection_pos]
        token = get_first_item(self.token)

        s = current_corpus.find(token)

        if s + len(token) < len(current_corpus):
            self.update_token(current_corpus[s:s + 1 + len(token)])
        
    def left_shrink_token(self):
        """
        Shrink the token by 1 character from the left of the current selected corpus
        """
        current_corpus = self.current_corpus()[self.current_selection_pos]
        token = get_first_item(self.token)

        s = current_corpus.find(token)

        if len(token) > 1:
            self.update_token(current_corpus[s + 1:s + len(token)])
        
    def right_shrink_token(self):
        """
        Shrink the token by 1 character from the right of the current selected corpus
        """
        current_corpus = self.current_corpus()[self.current_selection_pos]
        token = get_first_item(self.token)

        s = current_corpus.find(token)

        if len(token) > 1:
            self.update_token(current_corpus[s:s - 1 + len(token)])

    def get_selected_pos(self):
        return [self.current_selection_pos] if self.current_selection_pos is not None else []
    