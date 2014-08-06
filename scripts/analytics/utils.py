# -*- coding: utf-8 -*-

import datetime

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns


def plot_dates(dates, *args, **kwargs):
    """Plot date histogram.

    """
    fig = plt.figure()
    ax = fig.add_subplot(111)
    
    ax.hist(
        [mdates.date2num(each) for each in dates],
        *args, **kwargs
    )
    
    fig.autofmt_xdate()
    ax.format_xdata = mdates.DateFormatter('%Y-%m-%d')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    
    return fig

