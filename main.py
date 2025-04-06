import streamlit as st
from scraper import get_relevant_links, scrape_text
from pdf_processor import extract_text_from_pdf
from embeddings import store_text_in_supabase, get_relevant_text
from gemini_ai import ask_gemini
from supabase import create_client

import os
import io
import uuid
from dotenv import load_dotenv

load_dotenv()

# Supabase Client Setup
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME = "pdf"
TEMP_FOLDER = "temp_pdfs" 

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
st.set_page_config(page_title="j-Gpt", page_icon="📄")

def upload_to_supabase(uploaded_file):
    """Uploads a PDF file to Supabase Storage and returns the public URL."""
    file_name = uploaded_file.name  
    temp_path = os.path.join(TEMP_FOLDER, file_name)  

    # Save the file as a temporary file
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Define the storage path inside Supabase
    unique_id = uuid.uuid4().hex[:8]  # Generate a short unique ID
    file_path = f"{unique_id}_pdfs/{file_name}"
    
    # Upload the file
    res = supabase.storage.from_(BUCKET_NAME).upload(file_path, temp_path, file_options={"content-type": "application/pdf"})

    # Check if the upload was successful
    if hasattr(res, "error") and res.error:
        raise Exception(f"Upload failed: {res.error}")

    # Get the public URL of the uploaded file
    file_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path)

    # Delete the temporary file after upload
    os.remove(temp_path)

    return file_url

# Initialize session state for chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

with st.sidebar:
    st.markdown("<h1 style='color: #967ea7;'>Welcome to AskDocX</h1>", unsafe_allow_html=True)
    st.write("Your smart AI assistant for extracting insights from documents and web sources.")

    option = st.radio("Choose Your Content Source:", ("Upload PDFs", "Enter Website URL"))
    os.makedirs(TEMP_FOLDER, exist_ok=True)

    # File Upload Section
    if option == "Upload PDFs":
        uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

        if uploaded_files and st.button("📤 Process PDFs"):
            with st.spinner("Processing PDFs..."):
                #  Delete previous embeddings at the start of a new batch upload
                supabase.table("chunks").delete().neq("sentence", "").execute()
                supabase.table("pdf_files").delete().neq("file_name", "").execute()
                for uploaded_file in uploaded_files:
                    pdf_text = extract_text_from_pdf(uploaded_file)
                    file_url = upload_to_supabase(uploaded_file)
                    st.markdown(f"Uploaded: [{uploaded_file.name}]({file_url})", unsafe_allow_html=True)

                    if file_url:
                        # Store file metadata in `pdf_files` table
                        supabase.table("pdf_files").insert({"file_name": uploaded_file.name, "file_url": file_url}).execute()

                        # ✅ Store embeddings for each PDF
                        store_text_in_supabase(pdf_text, uploaded_file.name, file_url)

            st.success("✅ PDFs uploaded and processed successfully!")

    # 🌐 Web Scraping Section
    elif option == "Enter Website URL":
        domain_url = st.text_input("Enter website URL:")
      
        if domain_url and st.button("🔍 Scrape Website"):
            with st.spinner("Scraping website..."):
                supabase.table("chunks").delete().neq("sentence", "").execute()
                relevant_pages = get_relevant_links(domain_url)
                web_text = scrape_text(relevant_pages)
                store_text_in_supabase(web_text, "Website Content", domain_url)

            st.success("✅ Website content processed successfully!")
# Display chat history
if st.session_state.chat_history:
    for chat in st.session_state.chat_history:
        st.markdown(f"<p style='color: #967ea7; font-weight: bold;'>Q: {chat['question']}</p>", unsafe_allow_html=True)
        st.markdown(f"**A:** {chat['answer']}")
        if chat['results']:
            for result in chat['results']:
                st.markdown(f"📄 **Source:** <a href='{result['file_url']}' target='_blank' style='text-decoration: none; color: #967ea7; font-weight: bold;'>{result['file_name']}</a>", unsafe_allow_html=True)
                break




# Custom styling for ChatGPT-like UI
st.markdown("""
    <style>
        .stTextInput > div > div {
            border-radius: 20px;
            padding: 8px;
            
        }
        .send-button > button {
            border-radius: 90%;
            width: 50px;
            height: 50px;
            background-color: black; /* Dark purple */
            color: white;
            font-size: 20px;
            border: none;
        }
      
        .stTextInput input {
            font-size: 16px;
        }
    </style>
""", unsafe_allow_html=True)

# Align input field and button in one row
col1, col2 = st.columns([8, 1])
with col1:
    question = st.text_input("", placeholder="Have a Question? Ask Here..", key="question_input", label_visibility="collapsed")

with col2:
    send_button = st.button("➤", key="send_button", help="Send", use_container_width=True)

# Processing logic
if send_button and question:
    with st.spinner("Searching for relevant information..."):
        results = get_relevant_text(question)
        answer = ask_gemini(question, results)

    if answer:
        st.session_state.chat_history.append({"question": question, "answer": answer, "results": results})
        st.markdown("<h3 style='color: #967ea7;'>Answer:</h3>", unsafe_allow_html=True)
        st.markdown(answer)

        if results:
            for result in results:
               st.markdown(f"📄 **Source:** <a href='{result['file_url']}' target='_blank' style='text-decoration: none; color: #967ea7; font-weight: bold;'>{result['file_name']}</a>", unsafe_allow_html=True)
               break
        else:
            st.warning("❌ No relevant information found.")
    else:
        st.warning("❌ No answer found.")