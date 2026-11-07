# Week-1 kit: corpus, schema, annotation guide, eval skeleton
Install the rag-data-for-team zip folder
Unzip it into the repository root (folders merge with yours), make sure it is data/processed and data/index. Then:

```bash
# install all of the required packages
pip install -r requirements.txt         
pytest                                   # 7 tests should pass
```
Install Ollama via terminal for Windows 11
```bash
ollama --version                         # check if ollama's already existed

# open Powershell or Command Prompt (Run as administrator)
winget install --id=Ollama.Ollama -e

# install and run the model (in this case: Llama 3.2)
ollama run llama3.2:3b
```
run ```npm ci``` in the frontend folder (softwareengineeringfrontend)

Read in this order: `docs/00_week1_checklist.md` → `01_corpus_v0_guide.md` → `03_annotation_guide.md` → `02_chunk_schema.md` → `04_eval_skeleton.md`.

