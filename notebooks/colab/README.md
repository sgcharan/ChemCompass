# Google Colab notebooks

1. `01_corpus_cleanup.ipynb` — vision repair for flagged PYQ rows → `pyq-corpus-v1.jsonl`
2. `02_build_embeddings.ipynb` — optional FAISS semantic index
3. `03_mcq_synth_dataset.ipynb` — batch MCQ JSONL via local or deployed API
4. `04_lora_finetune.ipynb` — optional LoRA on synthesized pairs

Upload `data/pyq-corpus/corpus.jsonl` and `corpus.sqlite` from the repo after running `pyq_extract.corpus_cli`.
