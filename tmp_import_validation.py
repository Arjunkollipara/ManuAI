import fastapi, uvicorn, sqlalchemy, pandas, numpy
import sklearn, pyarrow
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import AzureChatOpenAI
from crewai import Agent, Task, Crew, Process
import chromadb
print('ALL IMPORTS OK')
print('fastapi:', fastapi.__version__)
print('langchain_chroma: ok')
print('crewai: ok')
print('chromadb:', chromadb.__version__)
