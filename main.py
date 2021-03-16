from dull import UI
from config import config
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('corpus_path')
    parser.add_argument('tokens_path')

    args = parser.parse_args()

    ui = UI(args.corpus_path, args.tokens_path, config['Save'], config['UI']['options'], config['Input']['tokens_cols'], config['UI']['display_range'], filter_na_cols=config['Input']['filter_na_cols'])
    ui.start()
