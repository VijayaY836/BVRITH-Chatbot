# BVRIT FAQ Chatbot

## Setup
1. Create a `.env` file from `.env.example` and add your OpenRouter key.
2. Install dependencies: `pip install -r requirements.txt`
3. Run the app: `streamlit run app.py`
4. Run evaluation: `python evaluate.py`

## Notes
- The knowledge base is sourced from `knowledge.md`.
- The vector store is persisted locally in the `chroma_db` folder.
- The evaluation report is written to `evaluation_report.json`.
