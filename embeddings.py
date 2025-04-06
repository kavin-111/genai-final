from sentence_transformers import SentenceTransformer
import json
from supabase import create_client
import os
from dotenv import load_dotenv


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
model = SentenceTransformer("all-MiniLM-L6-v2")

def store_text_in_supabase(text, file_name, file_url):
    """Encodes and stores text embeddings in Supabase along with file details."""

    sentences = text.split(". ")
    embeddings = model.encode(sentences)

    data = [
        {
            "sentence": sentences[i],
            "embedding": json.dumps(embeddings[i].tolist()),
            "file_name": file_name,
            "file_url": file_url
        }
        for i in range(len(sentences))
    ]

    supabase.table("chunks").insert(data).execute()


def get_relevant_text(query):
    """Retrieves relevant text snippets along with file links."""
    query_embedding = model.encode([query]).tolist()[0]
    response = supabase.rpc("top_matches", {
        "query_embedding": json.dumps(query_embedding),
        "match_threshold": 0.5,
        "match_count": 10
    }).execute()

    if response.data:
        return [
            {"sentence": item["sentence"], "file_name": item["file_name"], "file_url": item["file_url"]}
            for item in response.data
        ]
    return []
