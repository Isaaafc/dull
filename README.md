# Dull - tool for manual tokenization

Interface to help with tokenization. It allows referring to a corpus to specify the correct tokens and translations.

## Set up environment

### Using [Poetry](https://python-poetry.org/docs/)
```
poetry install
```

### Using pip
```
pip install requirements.txt
```

## Usage

### Corpus and tokens list

The program requires two files: *corpus.txt* and *tokens.txt*. The corpus should be a CSV file containing a line of original text and a token for each row:

```
id,short_event_description,preprocessed_tokens
0,SPR 搭建上落梯及工作台后才进行拆板工作,SPR
0,SPR 搭建上落梯及工作台后才进行拆板工作,搭建
0,SPR 搭建上落梯及工作台后才进行拆板工作,落梯
0,SPR 搭建上落梯及工作台后才进行拆板工作,工作台
0,SPR 搭建上落梯及工作台后才进行拆板工作,进行
0,SPR 搭建上落梯及工作台后才进行拆板工作,拆板
0,SPR 搭建上落梯及工作台后才进行拆板工作,工作
```

The tokens list should contain a list of tokens, their translations, and a set of options for tagging.

```
id,token,translation,frequency,formal_term_chi,formal_term_eng,is_construction_term,is_entity_name,is_typo,is_tokenization_error
8,升降台,Lifts ,14545,,,y,,,
17,工作台,Workbench ,8653,,,y,,,
```

### Running the program

```
python main.py corpus.txt tokens.txt
```
