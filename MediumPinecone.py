from airflow import DAG
from airflow.decorators import task
from airflow.models import Variable
from datetime import datetime, timedelta
import pandas as pd
import requests
import os
import time
import logging
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec

DATA_DIR = '/tmp/medium_data'
INDEX_NAME = 'semantic-search-fast'
BATCH_SIZE = 100
MODEL_NAME = 'all-MiniLM-L6-v2'

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False,
    'email_on_retry': False,
}

with DAG(
    dag_id='Medium_to_Pinecone',
    default_args=default_args,
    description='Search Medium posts using Pinecone',
    schedule_interval=timedelta(days=7),
    start_date=datetime(2025, 4, 1),
    catchup=False,
    tags=['medium', 'pinecone', 'search'],
) as dag:

    @task
    def download_data():
        os.makedirs(DATA_DIR, exist_ok=True)
        url = 'https://s3-geospatial.s3.us-west-2.amazonaws.com/medium_data.csv'
        path = f"{DATA_DIR}/medium_data.csv"

        r = requests.get(url)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                f.write(r.content)
            return path
        else:
            raise Exception(f"Download failed: {r.status_code}")

    @task
    def preprocess_data(path):
        df = pd.read_csv(path)
        df['title'] = df['title'].astype(str).fillna('')
        df['subtitle'] = df['subtitle'].astype(str).fillna('')
        df['metadata'] = df.apply(lambda row: {'title': f"{row['title']} {row['subtitle']}"}, axis=1)
        df['id'] = df.get('id', pd.Series(range(len(df)))).astype(str)
        out_path = f"{DATA_DIR}/medium_preprocessed.csv"
        df.to_csv(out_path, index=False)
        return out_path

    @task
    def create_index():
        api_key = Variable.get("PINECONE_API_KEY")
        pc = Pinecone(api_key=api_key)

        if INDEX_NAME in pc.list_indexes().names():
            pc.delete_index(INDEX_NAME)

        pc.create_index(
            name=INDEX_NAME,
            dimension=384,
            metric='dotproduct',
            spec=ServerlessSpec(cloud = Variable.get("PINECONE_CLOUD", default_var="aws"),
            region = Variable.get("PINECONE_REGION", default_var="us-east-1"))
        )

        while not pc.describe_index(INDEX_NAME).status['ready']:
            time.sleep(1)

        return INDEX_NAME

    @task
    def embed_and_upload(path, index_name):
        api_key = Variable.get("PINECONE_API_KEY")
        df = pd.read_csv(path)
        model = SentenceTransformer(MODEL_NAME)
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)

        for i in range(0, len(df), BATCH_SIZE):
            batch = df.iloc[i:i + BATCH_SIZE].copy()
            metadata = batch['metadata'].apply(eval).tolist()
            texts = [m['title'] for m in metadata]
            embeddings = model.encode(texts)

            to_upsert = [{
                'id': str(row['id']),
                'values': embeddings[j].tolist(),
                'metadata': metadata[j]
            } for j, (_, row) in enumerate(batch.iterrows())]

            index.upsert(vectors=to_upsert)

        return index_name

    @task
    def test_query(index_name):
        api_key = Variable.get("PINECONE_API_KEY")
        model = SentenceTransformer(MODEL_NAME)
        pc = Pinecone(api_key=api_key)
        index = pc.Index(index_name)

        query = "what is ethics in AI"
        print(f"\n Searching for: '{query}'")
        vector = model.encode(query).tolist()

        results = index.query(
            vector=vector,
            top_k=5,
            include_metadata=True,
            include_values=False
        )

        print("\n Top 5 matching articles:")
        for match in results.matches:
            score = round(match.score, 4)
            title_snippet = match.metadata['title'][:100]
            print(f" - [{score}] {title_snippet}")


    # Task flow
    raw = download_data()
    prepped = preprocess_data(raw)
    index = create_index()
    upserted = embed_and_upload(prepped, index)
    test_query(upserted)
