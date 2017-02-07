#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 13 15:30:27 2017

@author: eendebakpt
"""

#%% Load packages
from imp import reload
import sys
import os
import numpy as np
import matplotlib
from matplotlib import pyplot as plt
import pandas as pd

import qcodes
import qtt
reload(qtt)
from qtt import pmatlab as pgeometry
import nvtools
from nvtools.nvtools import plotSection
from nvtools.nvtools import avg_steps, fmt
import sklearn

interpolated = False

#%% Load data
jumpdata = np.load(os.path.join(qcodes.config['user']['nvDataDir'], 'jdata.npy')).T
allData = np.load(os.path.join(qcodes.config['user']['nvDataDir'], 'jdata-alldata.npy')).T
df = pd.DataFrame(jumpdata[:, 0:6], columns=['time', 'gate', 'yellow', 'new', 'gate jump', 'yellow jump'])
labels = np.load(os.path.join(qcodes.config['user']['nvDataDir'], 'labels.npy'))

time = allData[:, 0]
yellow = allData[:, 1]
gate = allData[:, 2]
dt = np.median(np.diff(time))
jumpSelect = (np.diff(time) > 3 * dt) & (np.diff(time) < 30 * 60)
jumpSelect = np.append(jumpSelect, False)

#%% Plot data, add callback for easy viewing

#import pgeometry
#from qtt.pgeometry import plotCallback

plt.close(60)
ScatterFig = plt.figure(60)
plt.clf()
plt.jet()
df.plot(kind='scatter', x='gate jump', y='yellow jump', ax=plt.gca(), c=labels, cmap=matplotlib.cm.jet, linewidths=0, colorbar=False)
plt.title('Click on figure to view data')
Fig = plt.figure(10)
plt.clf()
pgeometry.tilefigs([ScatterFig, Fig])


def f(plotidx, *args, **kwargs):
    verbose = kwargs.get('verbose', 1)
    if verbose:
        print('plotidx = %s' % plotidx)
    plt.figure(Fig.number)
    plt.clf()
    dataidx = int(jumpdata[plotidx, 6])
    plotSection(allData, list(range(dataidx - 60, dataidx + 100)), jumpSelect, si=dataidx)
    plt.pause(1e-4)

pc = pgeometry.plotCallback(func=f, xdata=df['gate jump'], ydata=df['yellow jump'], scale=[1, 100], verbose=0)
cid = ScatterFig.canvas.mpl_connect('button_press_event', pc)

#%% Example of very simple approach to classification: just probabilities

encoder = sklearn.preprocessing.LabelEncoder()
encoder.fit(labels)
chars = encoder.classes_
lx = encoder.transform(labels)

char_indices = encoder.transform([-1, 0, 1, 2, 3, 4])
char_map = dict((c, i) for i, c in enumerate(chars))

bc = np.bincount(lx)
prob = bc / bc.sum()
print('probabilities %s' % fmt(prob))

y_pred = np.tile(prob, (len(labels), 1))
print('  avg number of steps: %.3f' % avg_steps(lx, y_pred))


#%% Only select 1 and 2 labels

def plotI(labels, i, *args, **kwargs):
    idx = (labels == i).nonzero()[0]
    plt.plot(idx, i + 0 * idx, *args, **kwargs)
    return idx

plt.figure(8)
plt.clf()
#plt.plot(labels, '-c')
plotI(labels, 1, '.r')
plotI(labels, 2, '.g')

idx = np.logical_or(labels == 1, labels == 2)
rlabels = labels[labels != 0]
rlabels = labels[idx]

plt.figure(10)
plt.clf()
plt.plot(rlabels, '.-c', alpha=.5)
plotI(rlabels, 1, '.g')
plotI(rlabels, 2, '.r')
plt.xticks([])

#plt.plot(range(len(rlabels)), rlabels==1, '.r')

# note: the 1 and 2 clusters are pretty alternating, let's use this in our prediction

#%% Also simple: after a 1 first a 2 before a new 1, etc.

onetwo = np.zeros(len(labels))
threefour = np.zeros(len(labels))
for ii, l in enumerate(labels):
    if ii == 0:
        continue
    if l == 1:
        onetwo[ii] = 1
    elif l == 2:
        onetwo[ii] = 2
    else:
        onetwo[ii] = onetwo[ii - 1]
    if l == 3:
        threefour[ii] = 3
    elif l == 4:
        threefour[ii] = 4
    else:
        threefour[ii] = threefour[ii - 1]

y_pred = np.tile(prob, (len(labels), 1))
y_pred[(onetwo[:-1] == 1).nonzero()[0] + 1, char_map[1]] = 0
y_pred[(onetwo[:-1] == 2).nonzero()[0] + 1, char_map[2]] = 0
y_pred[(threefour[:-1] == 3).nonzero()[0] + 1, char_map[3]] = 0
y_pred[(threefour[:-1] == 4).nonzero()[0] + 1, char_map[4]] = 0
print('  avg number of steps: %.3f' % avg_steps(lx, y_pred))

#%% Best possible for a a double 2-level model:
#
# Suppose we have two 2-level systems. With probability p system A flips,
# with probability q=1-p system B flips

from nvtools.nvtools import avg_steps, fmt


def generate_double2lvl(N, p, q):
    x = np.zeros(N,).astype(int)
    for ii in range(N - 1):
        if np.random.rand() <= p:
            x[ii + 1] = x[ii] ^ 1
        else:
            x[ii + 1] = x[ii] ^ 2

    return x

import time
nn = 50000
# nn=100
p = .35
t0 = time.time()
print(generate_double2lvl(100, p, 1 - p))
labels = generate_double2lvl(nn, p, 1 - p)


encoder = sklearn.preprocessing.LabelEncoder()
encoder.fit(labels)
alphabet = encoder.classes_


chars = sorted(list(set(labels)))
print('total chars:', len(chars))
char_indices = dict((c, i) for i, c in enumerate(chars))

labelsX = [char_indices[c] for c in labels]

bc = np.bincount(labelsX)
prob = bc / bc.sum()


print('probability of each of the classes: %s' % fmt(prob))

# FIXME: convert from classes to jumps....

from nvtools.nvtools import two_grams

gg = two_grams(alphabet, labels)

print('dt %.3f' % (time.time() - t0))

#gg /= (len(text)-1 )
plt.figure(100)
plt.clf()
plt.imshow(gg, interpolation='nearest')
plt.axis('image')
plt.colorbar()
plt.xlabel('Class label')
plt.ylabel('Next')

plt.xticks(range(len(alphabet)), alphabet)
plt.yticks(range(len(alphabet)), alphabet)

pgeometry.tilefigs([100])

y_pred2 = np.vstack((prob, gg[:, labelsX[:-1]].T))
#y_pred2 = np.vstack( (prob, gg[:, labelsX[1:]].T ) )
y_pred = np.tile(prob, (nn, 1))

av0 = avg_steps(labelsX, (1 / len(alphabet)) * np.ones((nn, len(alphabet))))

av1 = avg_steps(labelsX, y_pred, verbose=1)

av2 = avg_steps(labelsX, y_pred2, verbose=0)

print('dt %.3f' % (time.time() - t0))

print('  avg number of steps (0-grams): %.5f' % av0)
print('  avg number of steps (1-grams): %.5f' % av1)
print('  avg number of steps (2-grams): %.5f' % av2)
