from rich import print
from rich.panel import Panel

def display(token, corpus, trim=True):
    """
    Returns a panel with token as the title and corpus as the body

    Parameters
    ----------
    token:
        Token to display
    corpus:
        List[str] of the section of corpus to display
    trim:
        Whether to trim the result to show only the section that contains the first occurence of the token
    """
    content = [c.replace(token, f'[yellow]{token}') for c in corpus]
    return Panel('\n'.join(content), title=token)
