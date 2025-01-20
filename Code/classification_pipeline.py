# -*- coding: utf-8 -*-
"""

@author: Chris Lucas
"""

import pandas as pd

from classification.feature.selection import correlated_features
from classification.classifier import BalancedRandomForest
from classification.hyperparameter import grid_search
from classification.accuracy import cross_validation
from classification.feature.importance import mean_decrease_impurity
from utils.utils import merge_dataframes
import pdal
import json
import laspy
import pickle

# %% Load ground truth data
print("loading data..")

# las_path = "Code/Data/ResearchArea2_sub_3.las"
# # classes = ['veg', 'non_veg']
# # veg_pc = pd.read_csv('../Data/ResearchArea_veg.csv')
# # non_veg_pc = pd.read_csv('../Data/ResearchArea_nonveg.csv')
# # data = merge_dataframes({'veg': veg_pc, 'non_veg': non_veg_pc}, 'class')
# # del veg_pc, non_veg_pc
# las = laspy.read(las_path)
# # pass whole laz file to dataframe
# def las_to_df(las_file):
#     data = {}
#     for dimension in las_file.point_format.dimensions:
#         dim_name = dimension.name
#         data[dim_name] = las_file[dim_name]
#     return pd.DataFrame(data)

# data = las_to_df(las)

csv_path = "Code/Data/ResearchArea2_params.csv"
data = pd.read_csv(csv_path)

data['Classification'] = data['Classification'].replace({3: 0, 4: 0, 5: 1})
class_cat, class_indexer = pd.factorize(data['Classification'])
data['class_cat'] = class_cat

# %% Define the feature space
features = data.columns.drop(['class', 'class_cat', 'X', 'Y', 'Z', 'Classification',
                              'return_number', 'intensity', 'number_of_returns',
                               'synthetic', 'key_point', 'overlap'],
                             'ignore')
# anisotropy gets dropped for being highly correlated
features = features.drop(correlated_features(data, features, corr_th=0.98))

# %% Hyperparameter optimization using a grid search (Cross Validated)
param_dict = {'min_samples_leaf': [1, 5, 10],
              'min_samples_split': [2, 5, 10],
              'max_features': [None, 'sqrt', 'log2'],
              'ratio': [0.1, 0.3, 0.5]}

# gs_scores, param_grid = grid_search(data, features, 'class_cat', param_dict)
# with open('model.pkl', 'wb') as f:
#     pickle.dump(gs_scores, f)
with open('model.pkl', 'rb') as f:
    gs_scores = pickle.load(f)
# %% Cross Validation
cv_scores, conf_matrices = cross_validation(data, features, 'class_cat')

# %% Load all data
point_cloud = pd.read_csv(csv_path,
                          delimiter=',', header=0)

# %% Create final classifier
clf = BalancedRandomForest(n_estimators=1000,
                           max_features='log2',
                           min_samples_leaf=1,
                           min_samples_split=5,
                           ratio=0.4)
clf.fit(data[features], data['class_cat'])

# %% Assess feature importances
fi_scores = mean_decrease_impurity(clf, features)

# %% Classify vegetation / non-vegetation
classification = []
parts = 8
part = len(point_cloud)//parts
for i in range(parts):
    if i == parts-1:
        temp_pc = point_cloud.iloc[i*part:]
    else:
        temp_pc = point_cloud.iloc[i*part:(i+1)*part]
    preds = clf.predict(temp_pc[features])
    classification.extend(list(preds))

point_cloud['Classification'] = classification

# %% Save results
point_cloud.to_csv('Code/Data/veg_classification.csv',
                   columns=['X', 'Y', 'Z', 'Classification'],
                   index=False)
