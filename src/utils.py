"""
Shared utilities for the ML pipeline scripts.
"""

import pandas as pd


def per_stock(func, df):
    """Apply func to each stock's data separately, then recombine.
    
    Handles the Symbol column regardless of whether it appears as
    a regular column, an index level, or a named index.
    """
    if "Symbol" not in df.columns:
        if isinstance(df.index, pd.MultiIndex) and "Symbol" in df.index.names:
            df = df.reset_index(level="Symbol")
        elif df.index.name == "Symbol":
            df = df.reset_index()
        else:
            raise KeyError("'Symbol' not found as column or index level")

    result = df.groupby("Symbol", group_keys=False).apply(
        lambda g: func(g).assign(Symbol=g.name)
    )

    if "Symbol" not in result.columns:
        if isinstance(result.index, pd.MultiIndex) and "Symbol" in result.index.names:
            result = result.reset_index(level="Symbol")
        elif result.index.name == "Symbol":
            result = result.reset_index()

    return result
