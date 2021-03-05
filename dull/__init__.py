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
    def __init__(self, corpus_path, tokens_path, save_config, options, tokens_cols):
        self.data = pd.DataFrame()

        with open(corpus_path, 'r') as f:
            self.data['corpus'] = [l.strip() for l in f.readlines()]
        
        self.tokens = pd.read_csv(tokens_path)
        self.tokens_cols = tokens_cols

        savedir = save_config['save_dir']

        if not os.path.exists(savedir):
            os.mkdir(savedir)

        self.save_path = os.path.join(savedir, save_config['save_file_name'])
        self.backup_path = os.path.join(savedir, save_config['backup_file_name'])

        self.options = options
        
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
                        self.corpus_pos = max(0, self.corpus_pos - 10)
                    elif c == 's':
                        self.corpus_pos = min(len(self.current_corpus) - 10, self.corpus_pos + 10)
                    else:
                        self.selected[self.options[int(c) - 1]] = not self.selected[self.options[int(c) - 1]]
                elif c == ':':
                    self.msg = ':'
                elif self.msg[0] == ':':
                    if c == 'q':
                        self.msg = ':q\nExiting'
                        self.save(self.backup_path)
                        live.update(self.get_grid(), refresh=True)
                        exit(0)
                    elif c == 'e':
                        self.update_option()

                        self.msg = f':e\nSaving'
                        self.save(self.save_path)
                        self.msg = 'Saved'
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
        self.current_corpus = self.data.loc[self.data['corpus'].str.contains(self.tokens.iloc[pos]['token'])]['corpus']
        self.corpus_pos = 0

        r = self.tokens.iloc[pos][self.options]
        self.selected = {opt: r[opt] == 'y' for opt in self.options}

    def update_option(self):
        for opt in self.selected:
            self.tokens.iloc[self.token_pos, self.tokens.columns.get_loc(opt)] = 'y' if self.selected[opt] else None    
    
    def get_grid(self):
        token = [s for s in self.tokens.iloc[self.token_pos][self.tokens_cols]]

        layout = Layout()

        upper = Layout()
        upper.split(
            Layout(display_corpus(self.token_pos, token, self.current_corpus.tolist()[self.corpus_pos:self.corpus_pos + 10]), name='panel', ratio=4),
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
