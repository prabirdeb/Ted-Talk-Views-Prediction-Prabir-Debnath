# -*- coding: utf-8 -*-
"""Deployment Code Ted Talk Views Prediction.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/13IaV7JVbAZzvig40ZxqGYBy1V1eS4IfF

**Ted Talk Views Prediction**
"""

# Importing libraries
import numpy as np
import pandas as pd
from numpy import math
import ast
from datetime import datetime
from datetime import date
import re

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.svm import SVR

import nltk
nltk.download('stopwords')
import string
from nltk.corpus import stopwords

# # For test
# ted_talk_df=pd.read_csv('/content/drive/MyDrive/Almabetter Assignments/Capstone projects/Ted Talk Views Prediction-Prabir Debnath/data_ted_talks_half.csv')

# Reading the data as pandas dataframe
ted_talk_df=pd.read_csv('data_ted_talks_half.csv')

def data_prep():
  global ted_talk_df

  # Finding out the relavant features from the deeper understanding of the data
  relavant_features=['occupations', 'views', 'published_date',
                   'native_lang', 'duration', 'topics','speaker_1','title']

  # Creating new df with relavant features
  ted_talk_df_clean=ted_talk_df[relavant_features]

  # Imputaion of null values of occupation with emty dict string
  ted_talk_df_clean['occupations']=ted_talk_df_clean['occupations'].fillna("{0:[]}")

  # There are python literals as string in the categorical columns which need to be treated
  for col in ['occupations', 'topics']:
    ted_talk_df_clean[col]=[ast.literal_eval(i) for i in ted_talk_df_clean[col]]

  # extracting the list from the dict of occupations
  ted_talk_df_clean['occupations']=[i.get(0) for i in ted_talk_df_clean['occupations']]

  # Datetime is appearing as string and we are converting to datetime
  ted_talk_df_clean['published_date']=ted_talk_df_clean['published_date'].apply(lambda x : datetime.strptime(x,'%Y-%m-%d'))

  # Feature engineering on published date to to extract years run
  ted_talk_df_clean['published_year']=ted_talk_df_clean['published_date'].apply(lambda x : x.year)
  ted_talk_df_clean['base_year']=2021
  ted_talk_df_clean['years_run']=(ted_talk_df_clean['base_year']-ted_talk_df_clean['published_year'])

  ted_talk_df_clean.drop(['published_date','base_year','published_year'], axis = 1, inplace=True)

  # There are very few experiences (only 1-27) for most of the 'native_lang' as compared to 'en' with count 3975. 
  # So, we are removing the exceptions in 'native_lang' category and creating a conditional df only for 'en'
  ted_talk_df_clean=ted_talk_df_clean.loc[(ted_talk_df_clean['native_lang']=='en')].reset_index()
  ted_talk_df_clean.drop('index', axis = 1, inplace=True)

  # Thus we are dropping the 'native_lang' column
  ted_talk_df_clean.drop('native_lang', axis = 1, inplace=True)

  # There are mixture of words in topics and occupations column.
  # Lets find out the main topics
  main_topics=[]
  for k in range(len(ted_talk_df_clean.topics)):
    common_terms=list(set([i[:3] for i in ted_talk_df_clean.occupations[k]]).intersection(set([i[:3] for i in ted_talk_df_clean.topics[k]])))
    
    if len(common_terms)!=0:
      for i in range(len(common_terms)):
        pattern = re.compile("%s" % common_terms[i])
        topics=[x for x in ted_talk_df_clean.topics[k] if pattern.match(x)][0]
    else:
      topics='unknown'

    main_topics.append(topics)

  ted_talk_df_clean['main_topics']=main_topics

  ted_talk_df_clean.drop(['occupations'], axis = 1, inplace=True)

  topics_df=pd.DataFrame(ted_talk_df_clean.groupby('main_topics')['views'].mean().sort_values(ascending=False))
  
  # There is a great portion of 'unkown' topics which need to be treated
  # Now, we can divide topics into three categories: Highly Favourite:2, Medium Favourite:1, Least Favourite:0
  topics_df.rename(columns={'views':'views_mean'},inplace=True)
  least_favourite=set(topics_df[(topics_df.views_mean<0.2*10**7)].index)-{'unknown'}
  medium_favourite=set(topics_df[(topics_df.views_mean>=0.2*10**7) & (topics_df.views_mean< 0.5*10**7)].index)-{'unknown'}
  highly_favourite=set(topics_df[(topics_df.views_mean>=0.5*10**7)].index)-{'unknown'}

  topics_cat=[]
  for k in ted_talk_df_clean.topics:
    topics_least_favourite_match=len(list(set(k).intersection(least_favourite)))
    topics_medium_favourite_match=len(list(set(k).intersection(medium_favourite)))
    topics_highly_favourite_match=len(list(set(k).intersection(highly_favourite)))

    if (topics_least_favourite_match>topics_medium_favourite_match) & (topics_least_favourite_match>topics_highly_favourite_match):
      topics_cat.append(0)
    elif (topics_medium_favourite_match>topics_least_favourite_match) & (topics_medium_favourite_match>topics_highly_favourite_match):
      topics_cat.append(1)
    else:
      topics_cat.append(2)

  ted_talk_df_clean['topics_cat']=topics_cat

  ted_talk_df_clean.drop(['topics', 'main_topics'], axis = 1, inplace=True)

  speaker_df=pd.DataFrame(ted_talk_df_clean.groupby('speaker_1')['views'].mean().sort_values(ascending=False))
  
  # Thus we can divide speakers into three categories: Highly Famous:2, Medium Famous:1, Least Famous:0
  speaker_df.rename(columns={'views':'views_mean'},inplace=True)
  ted_talk_df_clean = ted_talk_df_clean.merge(speaker_df,on = 'speaker_1',how = 'left')
  ted_talk_df_clean['speaker_cat'] = ted_talk_df_clean['views_mean'].apply(lambda x : 0 if x < 0.4*10**7 else (1 if 0.4*10**7 <= x < 0.8*10**7 else 2))

  ted_talk_df_clean.drop(['speaker_1','views_mean'],axis=1,inplace=True)

  # Lets understand the sentiment of the title and encode 

  ted_talk_df_clean['title'] = ted_talk_df_clean['title'].apply(text_process)

  # Extracting the highly attractive words from title
  highly=''
  for k in ted_talk_df_clean[(ted_talk_df_clean['views']>0.8*10**7)]['title'].values:
    highly=highly+' '+k
  highly_attractive=set(highly.split())

  # Extracting the medium attractive words from title
  medium=''
  for k in ted_talk_df_clean[(ted_talk_df_clean['views']>=0.4*10**7) & (ted_talk_df_clean['views']<=0.8*10**7)]['title'].values:
    medium=medium+' '+k
  medium_attractive=set(medium.split())

  # Extracting the least attractive words from title
  least=''
  for k in ted_talk_df_clean[(ted_talk_df_clean['views']<0.4*10**7)]['title'].values:
    least=least+' '+k
  least_attractive=set(least.split())

  highly_attractive_words=highly_attractive-highly_attractive.intersection(medium_attractive)-highly_attractive.intersection(least_attractive)
  medium_attractive_words=medium_attractive-medium_attractive.intersection(highly_attractive)-least_attractive.intersection(least_attractive)
  least_attractive_words=least_attractive-least_attractive.intersection(medium_attractive)-least_attractive.intersection(highly_attractive)

  # Title encoding
  title_cat=[]
  for k in ted_talk_df_clean.title:
    least_attractive_words_match=len(list(set(k.split()).intersection(least_attractive_words)))
    medium_attractive_words_match=len(list(set(k.split()).intersection(medium_attractive_words)))
    highly_attractive_words_match=len(list(set(k.split()).intersection(highly_attractive_words)))

    if (least_attractive_words_match>medium_attractive_words_match) & (least_attractive_words_match>highly_attractive_words_match):
      title_cat.append(0)
    elif (medium_attractive_words_match>least_attractive_words_match) & (medium_attractive_words_match>highly_attractive_words_match):
      title_cat.append(1)
    else:
      title_cat.append(2)

  ted_talk_df_clean['title_cat']=title_cat

  ted_talk_df_clean.drop(['title'],axis=1,inplace=True)

  # Arranging dependent feature in the last column
  dependent=ted_talk_df_clean.views.values
  ted_talk_df_clean.drop(['views'],axis=1,inplace=True)
  ted_talk_df_clean['views']=dependent    

  # There are only few experiences with more than 1*10^7 views. Thus we can remove these experiences
  ted_talk_df_clean=ted_talk_df_clean[ted_talk_df_clean['views'] < 1*10**7]

  # Creating dependent(output) and independent(input) variable
  dependent_variable='views'
  independent_variables=list(set(ted_talk_df_clean.describe().columns)-{dependent_variable})

  # Creating normalized input and output dataset
  X = np.log10(ted_talk_df_clean[['duration']])
  X[list(set(independent_variables)-{'duration'})]=ted_talk_df_clean[list(set(independent_variables)-{'duration'})]

  y = np.log10(ted_talk_df_clean[dependent_variable])

  # Imputation of infinite values with zero
  for col in X.columns:
    X[col].replace([np.inf, -np.inf], 0, inplace=True)

  y.replace([np.inf, -np.inf], 0, inplace=True)

  # Splitting of the data into Train and Test
  X_train, X_test, y_train, y_test = train_test_split(X, y, test_size = 0.2, random_state = 0)

  # Standardization of Input Data
  scaler = StandardScaler()
  X_train = scaler.fit_transform(X_train)
  X_test = scaler.transform(X_test)

  # Final model training
  model_svr_final=SVR(C= 6, gamma= 0.1)
  model_svr_final.fit(X_train, y_train)

  return X_train, scaler, model_svr_final

# We can divide title into three categories: Highly Attractive:2, Medium Attractive:1, Least Attractive:0
def text_process(text):
    nopunc =[char for char in text if char not in string.punctuation]
    nopunc=''.join(nopunc)
    return ' '.join([word for word in nopunc.split() if word.lower() not in stopwords.words('english')])

# Writing the function for predicting year of experience
def final_svr(duration, topics_cat, years_run, speaker_cat, title_cat):
  '''
  This function is predicting views for ted talk videos

  INPUT: 
  duration=int in seconds 
  topics_cat=Highly Favourite:2, Medium Favourite:1, Least Favourite:0 
  years_run=int in years 
  speaker_cat=Highly Famous:2, Medium Famous:1, Least Famous:0
  title_cat=Highly Attractive:2, Medium Attractive:1, Least Attractive:0
  OUTPUT: y_test_preds_cat: predicted views for ted talk videos
  
  '''
  try:

    X_train, scaler, model_svr_final=data_prep()
    
    # Creating numpy array from the input
    X_test=np.array([[duration, topics_cat, years_run, speaker_cat, title_cat]])
    # log transformation on duration
    X_test=np.array([[duration, topics_cat, years_run, speaker_cat, title_cat]])
    a=np.log10(X_test[:,:1])
    b=X_test[:,1:]
    X_test=np.concatenate((a,b),axis=1)
    # scaling of the input
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
      
    # Checking model performance for test set
    y_test_preds_cat = 10**model_svr_final.predict(X_test)

  except:
    y_test_preds_cat=np.array([0])
    print("Sorry ! Please check your input!")
  
  return np.around(y_test_preds_cat, 2)[0]

# Streamlit Project
import streamlit as st # All the text cell will be displayed after this import statement

st.title("Ted Talk Videos Views Prediction")
st.header("Note for Topic Cat, Speaker Cat and Title Cat: Highly Favourite:2, Medium Favourite:1, Least Favourite:0 ")

duration = st.number_input("Duration (seconds)")

topics_cat= st.number_input("Topic Cat (0, 1 or 2)")

years_run = st.number_input("Years Run")

speaker_cat = st.number_input("Speaker Cat (0, 1 or 2)")

title_cat = st.number_input("Title Cat (0, 1 or 2)")

ans = final_svr(duration, topics_cat, years_run, speaker_cat, title_cat)

if(st.button('PREDICT')):   # display the ans when the submit button is clicked
  st.success(ans)

