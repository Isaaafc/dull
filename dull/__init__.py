from pandas._config.config import options
from pandas.core.algorithms import SelectNSeries
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
import pandas as pd
import click
import os
import csv

__version__ = '0.1.0'

controls = ['w', 's', 'd', 'a']

instruction = '\n'.join([
    'a: previous token',
    'd: next token',
    'w: scroll up corpus',
    's: scroll down corpus',
    'numbers: toggle tag',
    ':q: quit',
    ':e: save',
    ':(number): go to token'
])

def display_corpus(pos, token, corpus):
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
    """
    _tok = token[0] if type(token) is list else token

    content = [c.replace(_tok, f'[yellow]{_tok}[/yellow]') for c in corpus]
    return Panel('\n'.join(content), title='{}. {}'.format(pos, ' | '.join(token)))

def display_tokenized_corpus(pos, token, tokenized_corpus):
    """
    Returns a panel with token as the title and tokenized corpus as the body

    Parameters
    ----------
    pos:
        Position of token
    token:
        Token to display
    tokenized_corpus:
        List[List[str]] of the section of tokenized corpus to display
    trim:
        Whether to trim the result to show only the section that contains the first occurence of the token
    """
    _tok = token[0] if type(token) is list else token

    content = [[f'[yellow]{t}[/yellow]' if t == _tok else t for t in c] for c in tokenized_corpus]
    return Panel('\n'.join(content), title='{}. {}'.format(pos, ' | '.join(token)))

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
    def __init__(self, corpus_path, tokens_path, save_config, options, tokens_cols, display_range=20, corpus_col_name='corpus', tokenized_col_name='preprocessed_tokens'):
        self.data = pd.read_csv(corpus_path)
        self.tokenized_col_name = tokenized_col_name
        self.corpus_col_name = corpus_col_name

        self.tokens = pd.read_csv(tokens_path)
        self.tokens_cols = tokens_cols

        savedir = save_config['save_dir']

        if not os.path.exists(savedir):
            os.mkdir(savedir)

        self.save_path = os.path.join(savedir, save_config['save_file_name'])
        self.backup_path = os.path.join(savedir, save_config['backup_file_name'])

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
                c = click.getchar()

                if not (len(self.msg) and self.msg[0] == ':') and c in controls + [str(i + 1) for i in range(len(self.options))]:
                    if c == 'a':
                        self.update_option()
                        self.goto_token((self.token_pos - 1) % len(self.tokens))
                    elif c == 'd':
                        self.update_option()
                        self.goto_token((self.token_pos + 1) % len(self.tokens))
                    elif c == 'w':
                        self.display_state.scroll_down()
                    elif c == 's':
                        self.display_state.scroll_up()
                    else:
                        self.selected[self.options[int(c) - 1]] = not self.selected[self.options[int(c) - 1]]
                elif c == ':':
                    self.msg = ':'
                elif self.msg[0] == ':':
                    if c == 'q':
                        self.msg = ':q\nExiting'

                        try:
                            self.save(self.backup_path)
                            live.update(self.get_grid(), refresh=True)
                            exit(0)
                        except PermissionError:
                            self.msg = 'Save failed. Check if the file is opened in another program.'
                            live.update(self.get_grid(), refresh=True)
                    elif c == 'e':
                        self.update_option()

                        try:
                            self.msg = f':e\nSaving'
                            self.save(self.save_path)
                            self.msg = 'Saved'
                        except:
                            self.msg = 'Save failed. Check if the file is opened in another program.'
                            live.update(self.get_grid(), refresh=True)
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

                live.update(self.get_grid(), refresh=True)

    def goto_token(self, pos):
        self.token_pos = pos

        current_corpus = self.data.loc[self.data[self.tokenized_col_name] == self.tokens.iloc[pos]['token']][self.corpus_col_name].unique()

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
    
    def get_grid(self):
        layout = Layout()

        upper = Layout()
        upper.split(
            Layout(display_corpus(self.token_pos, self.display_state.token, self.display_state.current_corpus()), name='panel', ratio=4),
            Layout(Panel(instruction, title='Controls', expand=False), name='instruction', ratio=1),
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

    def save(self, save_path):
        self.tokens.to_csv(save_path, index=False, encoding='utf-8')

class DisplayState():
    """
    Represents the display state for a *single* token
    """
    def __init__(self, corpus, token, display_range, corpus_pos=0):
        self.corpus = corpus
        self.token = token
        self.display_range = display_range
        self.corpus_pos = corpus_pos
        self.current_selection_pos = None

    def scroll_down(self):
        self.corpus_pos = min(len(self.corpus) - self.display_range, self.corpus_pos + self.display_range)
    
    def scroll_up(self):
        self.corpus_pos = min(len(self.corpus) - self.display_range, self.corpus_pos + self.display_range)

    def current_corpus(self):
        return self.corpus[self.corpus_pos:self.corpus_pos + self.display_range]

    def scroll_down_selection(self):
        self.current_selection_pos = (self.current_selection_pos + 1) % len(self.corpus) if self.current_selection_pos else 1
    
    def scroll_up_selection(self):
        self.current_selection_pos = (self.current_selection_pos - 1) % len(self.corpus) if self.current_selection_pos else 1

    def edit_token(self):
        pass
