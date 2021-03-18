from dull import utils
import pytest
import pandas as pd

@pytest.mark.parametrize('pos', [0, 1, 2])
def test_ins_pos(pos):
    df = pd.DataFrame([{'a': 1, 'b': 2}, {'a': 4, 'b': 5}])
    new_row = {'a': 6, 'b': 7}
    
    df = utils.ins_pos(df, new_row, pos)

    assert df.iloc[pos]['a'] == 6 and df.iloc[pos]['b'] == 7
    assert len(df) == 3

@pytest.mark.parametrize('pos', [0, 1, 2])
def test_drop_by_iloc(pos):
    df = pd.DataFrame([{'a': 1, 'b': 2}, {'a': 4, 'b': 5}, {'a': 1, 'b': 2}])
    df_dropped = utils.drop_by_iloc(df, pos)
    
    assert df_dropped.equals(df.drop(index=pos))
