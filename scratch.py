import termplotlib as tpl
from termplotlib.hist import hist_horizontal, hist_vertical
import numpy as np

rng = np.random.default_rng(123)
sample = rng.standard_normal(size=1000)
counts, bin_edges = np.histogram(sample)

lines = hist_vertical(counts, bar_width=1)
print("\n".join(lines))
