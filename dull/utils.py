import pandas as pd

def get_first_item(item):
    return item[0] if type(item) is list else item

def ins_pos(df, row, pos):
    """
    Insert a new row into a position in df. The new row will be at df.iloc[pos]

    Parameters
    ----------
    df:
        DataFrame to insert into
    row:
        New row
    pos:
        Position to insert into
    """
    df_head = df.iloc[:pos]
    df_tail = df.iloc[pos:]
    df_head = df_head.append(row, ignore_index=True)

    return pd.concat([df_head, df_tail], ignore_index=True)

def drop_by_iloc(df, pos):
    """
    Delete a row in df by iloc

    Parameters
    ----------
    df:
        DataFrame to delete from
    pos:
        iloc pos to delete
    """
    return df.drop(index=df.iloc[pos:pos + 1].index[0])
