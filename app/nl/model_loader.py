import os
from typing import Tuple

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM
from app.settings import NLSQL_MODEL_ID, NLSQL_MAX_NEW_TOKENS, TRANSFORMERS_CACHE

# Tell Hugging Face to use fast transfer if available
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
CACHE_DIR = str(TRANSFORMERS_CACHE)

# Global singletons to avoid reloading on every request
_tokenizer = None
_model = None
_is_seq2seq = False


def load_model() -> Tuple[AutoTokenizer, torch.nn.Module, bool]:
    """
    Load the Hugging Face model defined in settings.
    Tries a causal LM first, then falls back to a seq2seq LM.
    Keeps the model in global variables so it's only loaded once.
    """
    global _tokenizer, _model, _is_seq2seq

    # Prefer MPS if available, else CPU
    device = "cpu"
    if (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
        and torch.backends.mps.is_built()
    ):
        device = "mps"

    # Load tokenizer
    tok = AutoTokenizer.from_pretrained(
        NLSQL_MODEL_ID, use_fast=True, cache_dir=CACHE_DIR, trust_remote_code=True
    )
    # Ensure a pad token exists for generation
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token or tok.unk_token or "</s>"

    # Load model weights, preferring causal LM
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
        # If causal load fails, fall back to seq2seq LM (e.g., T5 family)
        model = AutoModelForSeq2SeqLM.from_pretrained(
            NLSQL_MODEL_ID,
            cache_dir=CACHE_DIR,
            torch_dtype=torch.float16 if device == "mps" else torch.float32,
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )
        is_seq2seq = True

    # Move model to CPU or MPS
    model.to(device)

    # Cache globally
    _tokenizer, _model, _is_seq2seq = tok, model, is_seq2seq
    return _tokenizer, _model, _is_seq2seq


def generate(prompt: str, max_new_tokens: int | None = None) -> str:
    """
    Run deterministic (greedy) text generation using the loaded model.
    Loads the model on first call if needed.
    Returns only the generated completion (without the prompt for causal models).
    """
    global _tokenizer, _model, _is_seq2seq
    if _tokenizer is None or _model is None:
        load_model()

    tok, model, is_seq2seq = _tokenizer, _model, _is_seq2seq
    device = next(model.parameters()).device
    max_new = max_new_tokens or NLSQL_MAX_NEW_TOKENS

    # Tokenize input and move to correct device
    enc = tok(prompt, return_tensors="pt", padding=False, truncation=True).to(device)

    # Generate output tokens
    with torch.no_grad():
        out_ids = model.generate(
            **enc,
            max_new_tokens=max_new,
            do_sample=False,     # greedy decoding
            num_beams=1,
            use_cache=True,
            eos_token_id=tok.eos_token_id or tok.pad_token_id,
            pad_token_id=tok.pad_token_id or tok.eos_token_id,
        )

    # Decode output to string
    if is_seq2seq:
        # Seq2seq models output only the completion
        return tok.decode(out_ids[0], skip_special_tokens=True).strip()
    else:
        # Causal models output prompt + completion; strip the prompt tokens
        prompt_len = enc["input_ids"].shape[-1]
        return tok.decode(out_ids[0][prompt_len:], skip_special_tokens=True).strip()
