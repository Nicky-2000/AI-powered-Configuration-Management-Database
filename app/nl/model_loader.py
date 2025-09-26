# app/nl/model_loader.py
import os
from typing import Tuple

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM
from app.settings import NLSQL_MODEL_ID, NLSQL_MAX_NEW_TOKENS, TRANSFORMERS_CACHE

# cache dir for Hugging Face
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
CACHE_DIR = str(TRANSFORMERS_CACHE)

# --- single global model ---
_tokenizer = None
_model = None
_is_seq2seq = False


def load_model() -> Tuple[AutoTokenizer, torch.nn.Module, bool]:
    """
    Always load the model specified in app.settings.NLSQL_MODEL_ID.
    Call this once at startup or before first generate().
    """
    global _tokenizer, _model, _is_seq2seq

    device = "cpu"
    if (
        os.getenv("NLSQL_DEVICE", "").lower() in ("mps", "metal")
        and hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
        and torch.backends.mps.is_built()
    ):
        device = "mps"

    tok = AutoTokenizer.from_pretrained(
        NLSQL_MODEL_ID, use_fast=True, cache_dir=CACHE_DIR, trust_remote_code=True
    )
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token or tok.unk_token or "</s>"

    # try causal first, fallback to seq2seq
    try:
        model = AutoModelForCausalLM.from_pretrained(
            NLSQL_MODEL_ID,
            cache_dir=CACHE_DIR,
            torch_dtype=torch.float16 if device == "mps" else torch.float32,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )
        is_seq2seq = False
    except Exception:
        model = AutoModelForSeq2SeqLM.from_pretrained(
            NLSQL_MODEL_ID,
            cache_dir=CACHE_DIR,
            torch_dtype=torch.float16 if device == "mps" else torch.float32,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )
        is_seq2seq = True

    model.to(device)

    _tokenizer, _model, _is_seq2seq = tok, model, is_seq2seq
    return _tokenizer, _model, _is_seq2seq


def generate(prompt: str, max_new_tokens: int | None = None) -> str:
    """
    Deterministic greedy generation.
    Always uses the model specified in app.settings.
    """
    global _tokenizer, _model, _is_seq2seq
    if _tokenizer is None or _model is None:
        load_model()

    tok, model, is_seq2seq = _tokenizer, _model, _is_seq2seq
    device = next(model.parameters()).device
    max_new = max_new_tokens or NLSQL_MAX_NEW_TOKENS

    enc = tok(prompt, return_tensors="pt", padding=False, truncation=True).to(device)

    with torch.no_grad():
        out_ids = model.generate(
            **enc,
            max_new_tokens=max_new,
            do_sample=False,
            num_beams=1,
            use_cache=True,
            eos_token_id=tok.eos_token_id or tok.pad_token_id,
            pad_token_id=tok.pad_token_id or tok.eos_token_id,
        )

    if is_seq2seq:
        return tok.decode(out_ids[0], skip_special_tokens=True).strip()
    else:
        prompt_len = enc["input_ids"].shape[-1]
        return tok.decode(out_ids[0][prompt_len:], skip_special_tokens=True).strip()
