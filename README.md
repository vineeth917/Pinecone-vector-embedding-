# **Medium Semantic Search with Pinecone and Airflow**

This project builds a semantic search engine on top of Medium articles using vector embeddings, Pinecone, and Airflow.

We download Medium post data, generate embeddings using a Sentence Transformer model (`all-MiniLM-L6-v2`), store them in Pinecone, and then enable natural language search on top of that data.

---

##  **Project Structure**

```bash
Pinecone-vector-embedding-/
├── dags/
│   └── Medium_to_Pinecone.py        # Airflow DAG definition
├── docker-compose.yaml              # Airflow + Postgres container setup
├── requirements.txt (optional)
└── README.md
```

---

## **How It Works (Airflow DAG Overview)**

The DAG runs weekly and executes the following tasks:

### 1. `download_data`

- Downloads Medium articles CSV from an S3 bucket

### 2. `preprocess_data`

- Cleans titles/subtitles and combines them into a metadata field

### 3. `create_index`

- Connects to Pinecone using your API key (via Airflow Variables)
- Deletes previous index (if any) and creates a new one with `dotproduct` metric

### 4. `embed_and_upload`

- Uses `all-MiniLM-L6-v2` to generate 384-dimension embeddings
- Uploads vectors to Pinecone with associated metadata

### 5. `test_query`

- Runs a sample query: `what is ethics in AI`
- Logs top 5 results

---

##  **How to Run It**

### 1. Clone the Repo

```bash
git clone https://github.com/yourname/Pinecone-vector-embedding-.git
cd Pinecone-vector-embedding-
```

### 2. Start Docker

```bash
docker-compose up --build
```

### 3. Open Airflow UI

Visit: [http://localhost:8081](http://localhost:8081)

### 4. Set Airflow Variable

In the Airflow UI:

- Navigate to `Admin > Variables`
- Add:
  - **Key:** `PINECONE_API_KEY`
  - **Value:** *(your Pinecone API key)*

### 5. Trigger the DAG

In the Airflow UI:

- Enable the DAG: `Medium_to_Pinecone`
- Click the **Trigger DAG ▶️** button

---

##  **Sample Output (Logged by **``** Task)**

```bash
Top 5 matching articles:
 - [0.741] Ethics in AI: Potential Root Causes for Biased Algorithms...
 - [0.717] The ethical implications of AI in design...
 - [0.6669] Ethical Considerations In Machine Learning Projects...
 - [0.6517] Navigating the Ethical Contours of AI Copy Generators...
```

These results were generated using semantic similarity on titles/subtitles of Medium posts. The model captures meaning rather than exact keywords, allowing flexible, human-like search.

---

##  **Conclusion**

This pipeline demonstrates:

- How to use `sentence-transformers` to generate embeddings
- How to store and search embeddings using Pinecone
- How to orchestrate it all with Apache Airflow in Docker

You now have a semantic search engine that supports flexible, natural queries over unstructured text.

---

##  **Next Ideas**

- Add a Streamlit or Flask app for real-time querying
- Persist all queries & results into a Postgres table
- Expand metadata with author, publish date, and links

---

##  **Credits**

Built by **[Vineeth Rayadurgam]**, using Sentence Transformers, Pinecone, and Airflow.

