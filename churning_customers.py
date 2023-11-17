# -*- coding: utf-8 -*-
"""Churning Customers.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/11NoqQ1ea8TsbG08fan2yVfETaKhKJo-D
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, LabelEncoder
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.metrics import make_scorer, accuracy_score, roc_auc_score
# !pip install scikeras
from scikeras.wrappers import KerasClassifier
from google.colab import drive
# !pip install streamlit
import streamlit as st

drive.mount('/content/drive')
df = pd.read_csv('/content/drive/My Drive/Colab Notebooks/CustomerChurn_dataset.csv')

"""**FEATURE EXTRACTION**"""

df.replace('', np.nan, inplace=True)
df.dropna(inplace=True)

# Features to extract
# selected_features = df.drop(['customerID'], axis = 1)
selected_features = [
    'gender', 'SeniorCitizen', 'Partner', 'Dependents', 'tenure', 'PhoneService',
    'MultipleLines', 'InternetService', 'OnlineSecurity', 'OnlineBackup',
    'DeviceProtection', 'TechSupport', 'StreamingTV', 'StreamingMovies',
    'Contract', 'PaperlessBilling', 'PaymentMethod', 'MonthlyCharges', 'TotalCharges']

# Extracting relevant features from the dataset
df_selected_features = df[selected_features]
df_selected = df[selected_features + ['Churn']]

"""**EXPLORATORY DATA ANALYSIS**"""
# Data Distribution
plt.figure(figsize=(15, 12))
df_selected.hist(bins=20, color='skyblue', edgecolor='black', layout=(3, 3), figsize=(15, 12))
plt.tight_layout()
plt.show()

# Outlier Detection using Box Plots
num_features = len(selected_features[:-1])
num_rows = int(np.ceil(num_features / 3))
num_cols = min(num_features, 3)

plt.figure(figsize=(15, 4 * num_rows))

for i, column in enumerate(selected_features[:-1], 1):
    plt.subplot(num_rows, num_cols, i)

    # Check if the column contains numeric data
    if df[column].dtype in ['int64', 'float64']:
        sns.boxplot(x='Churn', y=column, data=df)
    else:
        # Handle non-numeric or mixed-type data
        sns.countplot(x=column, hue='Churn', data=df)

plt.tight_layout()
plt.show()

# Churn Analysis
plt.figure(figsize=(6, 5))
sns.countplot(x='Churn', data=df)
plt.show()

# Feature Relationships
plt.figure(figsize=(20, 20))
# Select the top 7 features with the highest absolute correlation with the target variable 'Churn'
# top_features = df[numeric_features + categorical_features + ['Churn']].corr()['Churn'].abs().nlargest(8).index
# top_feature_corr = df[top_features].corr()

# Separate features into numeric and categorical
numeric_features = ['SeniorCitizen', 'tenure', 'MonthlyCharges', 'TotalCharges']
categorical_features = [col for col in df_selected if col not in numeric_features]

from scipy.stats import chi2_contingency


def correlation_ratio(categories, values):
    f_obs = pd.crosstab(categories, values)
    chi2, _, _, _ = chi2_contingency(f_obs)
    cr = np.sqrt(chi2 / (chi2 + len(categories) - 1))
    return cr


# Initialize a correlation matrix
corr_matrix = np.zeros((len(df[numeric_features].columns), len(df[categorical_features].columns)))

# Fill in the correlation matrix with correlation ratios
for i, num_col in enumerate(df[numeric_features].columns):
    for j, cat_col in enumerate(df[categorical_features].columns):
        corr_matrix[i, j] = correlation_ratio(df[cat_col], df[num_col])

# Create a heatmap
plt.figure(figsize=(10, 8))
sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", linewidths=0.5,
            xticklabels=df[categorical_features].columns, yticklabels=df[numeric_features].columns)
plt.title('Correlation Heatmap - Mixed Data')
plt.show()

# Customer Profiles and Churning
plt.figure(figsize=(12, 8))
sns.catplot(x='SeniorCitizen', hue='Partner', col='Dependents', row='Churn',
            data=df, kind='count', height=4, aspect=1.2)
plt.show()

"""**TRAINING AN MLP MODEL USING FUNCTION API**"""


# Training an MLP model using the Functional API
def create_mlp_model(input_dim, hidden_units=64, dropout_rate=0.3):
    input_layer = tf.keras.layers.Input(shape=(input_dim,))
    layer_1 = tf.keras.layers.Dense(hidden_units, activation='relu')(input_layer)
    layer_2 = tf.keras.layers.Dropout(dropout_rate)(layer_1)
    output = tf.keras.layers.Dense(1, activation='sigmoid')(layer_2)

    model = tf.keras.Model(inputs=input_layer, outputs=output)
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model


# Separate features into numeric and categorical
numeric_features = df_selected_features.select_dtypes(include=[np.number]).columns
categorical_features = df_selected_features.select_dtypes(exclude=[np.number]).columns

# Extract features and encoding target variable
encoder = OneHotEncoder(drop='first', sparse=False)
X_encoded = encoder.fit_transform(df_selected_features[categorical_features])
df_encoded_categorical = pd.DataFrame(X_encoded, columns=encoder.get_feature_names_out(categorical_features))
x = pd.concat([df_selected_features[numeric_features], df_encoded_categorical], axis=1)

y_encoded = encoder.fit_transform(df_selected[['Churn']])
y = pd.DataFrame(y_encoded, columns=encoder.get_feature_names_out(['Churn']))
df_encoded = pd.concat([x, y], axis=1)

# Extract features and target variable
# X = df_encoded.drop(columns = ['Churn_Yes']).values
# y = df_encoded['Churn_Yes'].values

# Hyperparameter tuning with GridSearchCV
mlp_model = KerasClassifier(build_fn=create_mlp_model, input_dim=x.shape[1], epochs=50, batch_size=128, hidden_units=32,
                            dropout_rate=0.8, verbose=0)

param_grid = {'hidden_units': [32, 64, 128], 'dropout_rate': [0.3, 0.5, 0.8]}

# scoring metric for GridSearchCV
scorer = make_scorer(roc_auc_score)

# Perform GridSearchCV with cross-validation
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
grid_search = GridSearchCV(estimator=mlp_model, param_grid=param_grid, scoring=scorer, cv=cv)
grid_result = grid_search.fit(x, y)

# Create a KerasClassifier wrapper for use in GridSearchCV
# mlp_model = KerasClassifier(build_fn=create_mlp_model, input_dim=X.shape[1], hidden_units=32, epochs=5, batch_size=32, dropout_rate=0.5, verbose=0)

"""**TESTING AND OPTIMIZATION**"""

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y)

# Standardize the data
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Using the best hyperparameters from GridSearchCV
best_hidden_units = grid_result.best_params_['hidden_units']
best_dropout_rate = grid_result.best_params_['dropout_rate']

# Creating and training the optimized model
optimized_model = create_mlp_model(input_dim=X_train.shape[1], hidden_units=best_hidden_units,
                                   dropout_rate=best_dropout_rate)
optimized_model.fit(X_train_scaled, y_train, epochs=250, batch_size=50, validation_split=0.2, verbose=0)
optimized_model.summary()

# Evaluating the model on the test set
y_pred_proba = optimized_model.predict(X_test_scaled)
y_pred_binary = (y_pred_proba > 0.5).astype(int)

# Calculating accuracy and AUC score
accuracy = accuracy_score(y_test, y_pred_binary)
auc_score = roc_auc_score(y_test, y_pred_proba)

# Print evaluation metrics
print(f"Test Accuracy: {accuracy:.4f}")
print(f"Test AUC Score: {auc_score:.4f}")


# Importing pickle to dump the file
import pickle
pickle.dump(optimized_model, open('/content/drive/My Drive/Colab Notebooks/Churning Customers.pkl', 'wb'))
