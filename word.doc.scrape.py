import os
import json
import requests
from datetime import datetime
from docx import Document

# Folders configuration
SOURCE_DIR = "SourceDocs"
ARCHIVE_DIR = "NewsArchive"

# Ensure directories exist
os.makedirs(SOURCE_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

def extract_text_from_docx(file_path):
    """Reads a .docx file and returns all its text."""
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        if para.text.strip():  # Skip blank lines
            full_text.append(para.text)
    return "\n".join(full_text)

def process_word_documents():
    # Find all .docx files in the source directory
    docx_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.docx')]
    
    if not docx_files:
        print(f"No Word documents found in '{SOURCE_DIR}' folder.")
        return

    report_data = []

    for file_name in docx_files:
        print(f"Reading: {file_name}...")
        file_path = os.path.join(SOURCE_DIR, file_name)
        
        # 1. Pull the text out of the Word File
        raw_text = extract_text_from_docx(file_path)
        
        # 2. Craft the Prompt for your Z13's Llama 3.1 70B model
        prompt = f"""
        You are a strict fact-extraction AI. 
        Analyze the following text from a document and extract ONLY verifiable facts.
        - Remove all opinions, fluff, background adjectives, and emotional bias.
        - Use clean bullet points.
        - If a claim cannot be verified directly by the text, exclude it entirely.
        
        DOCUMENT TEXT:
        {raw_text[:6000]} 
        """

        # 3. Send to your local Ollama instance
        print(f"Extracting facts via local LLM...")
        try:
            response = requests.post('http://localhost:11434/api/generate', 
                json={
                    "model": "llama3.1:70b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_ctx": 8192}
                })
            facts = response.json()['response']
            
            # Format to match your Streamlit UI expectations
            report_data.append({
                "title": file_name.replace(".docx", "").replace("-", " ").replace("_", " "),
                "category": "DOCUMENT",
                "url": f"Local File: {file_name}",
                "report": facts
            })
            
        except Exception as e:
            print(f"Error processing {file_name} with LLM: {e}")

    # 4. Save to a timestamped JSON file inside NewsArchive
    if report_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"doc_facts_{timestamp}.json"
        output_path = os.path.join(ARCHIVE_DIR, output_filename)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=4, ensure_ascii=False)
        print(f"Successfully created archive: {output_filename}")

if __name__ == "__main__":
    process_word_documents()