"""A minimal OpenAI-compatible chat server on transformers: the fallback when vLLM fails on the cluster.

It serves exactly what isochron sends: POST /v1/chat/completions with string messages, temperature,
top_p, top_k (0 = off), min_p (0 = off), max_tokens, seed and chat_template_kwargs. It also answers
GET /health (200 once the model is loaded), GET /v1/models and GET /version (read by
isochron.run.backend_info). Requests are generated one at a time. Sampling uses only the request's
settings: the model's generation_config.json defaults are not applied, as with vLLM's
--generation-config vllm. A request seed seeds torch before that request.

The API key comes from ISOCHRON_SERVER_KEY (never from the command line); requests must send it as
"Authorization: Bearer <key>". Bind to 127.0.0.1 only.

    ISOCHRON_SERVER_KEY=... python hpc/hf_server.py --model DIR --served-model-name NAME --port PORT [--kind multimodal]

--kind multimodal loads Apertus 1.5 the way its model card shows (AutoProcessor and
AutoModelForMultimodalLM, from the transformers fork); --kind causal loads a text model
(AutoTokenizer and AutoModelForCausalLM), such as Qwen3-14B for the judge.
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
import transformers
from transformers import GenerationConfig


class Model:
    def __init__(self, path: str, kind: str, dtype: str, device_map: str = "auto") -> None:
        self.path, self.kind, self.dtype = path, kind, dtype
        torch_dtype = getattr(torch, dtype)
        if kind == "multimodal":
            from transformers import AutoModelForMultimodalLM, AutoProcessor

            self.processor = AutoProcessor.from_pretrained(path)
            self.tokenizer = self.processor.tokenizer
            self.model = AutoModelForMultimodalLM.from_pretrained(path, dtype=torch_dtype, device_map=device_map).eval()
        else:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self.processor = self.tokenizer = AutoTokenizer.from_pretrained(path)
            self.model = AutoModelForCausalLM.from_pretrained(path, dtype=torch_dtype, device_map=device_map).eval()
        base = self.model.generation_config
        self.model.generation_config = GenerationConfig(
            bos_token_id=base.bos_token_id, eos_token_id=base.eos_token_id, pad_token_id=base.pad_token_id)
        self.lock = threading.Lock()

    def chat(self, body: dict) -> dict:
        messages = [{"role": m["role"], "content": m["content"]} for m in body["messages"]]
        inputs = self.processor.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
            **(body.get("chat_template_kwargs") or {})).to(self.model.device)
        temperature = float(body.get("temperature", 1.0))
        max_new = int(body.get("max_tokens") or 1024)
        settings: dict = {"max_new_tokens": max_new, "do_sample": temperature > 0}
        if temperature > 0:
            settings.update(temperature=temperature, top_p=float(body.get("top_p", 1.0)),
                            top_k=int(body.get("top_k") or 0), min_p=float(body.get("min_p") or 0) or None)
        with self.lock:
            if body.get("seed") is not None:
                torch.manual_seed(int(body["seed"]))
            with torch.inference_mode():
                out = self.model.generate(**inputs, **settings)
        n_in = inputs["input_ids"].shape[-1]
        new = out[0, n_in:]
        text = self.tokenizer.decode(new, skip_special_tokens=True)
        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}", "object": "chat.completion", "created": int(time.time()),
            "model": body.get("model"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                         "finish_reason": "length" if len(new) >= max_new else "stop"}],
            "usage": {"prompt_tokens": n_in, "completion_tokens": len(new), "total_tokens": n_in + len(new)},
        }


def make_handler(model: Model, name: str, key: str):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, obj: dict) -> None:
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _authorised(self) -> bool:
            sent = self.headers.get("Authorization", "")
            if hmac.compare_digest(sent.encode(), f"Bearer {key}".encode()):
                return True
            self._send(401, {"error": {"message": "invalid API key"}})
            return False

        def do_GET(self) -> None:
            if self.path == "/health":
                self._send(200, {"status": "ok"})
            elif self.path == "/version":
                self._send(200, {"server": "isochron-hf-server", "transformers": transformers.__version__,
                                 "torch": torch.__version__, "model_path": model.path, "dtype": model.dtype})
            elif self.path == "/v1/models" and self._authorised():
                self._send(200, {"object": "list", "data": [{"id": name, "object": "model", "root": model.path}]})
            elif self.path != "/v1/models":
                self._send(404, {"error": {"message": f"no route {self.path}"}})

        def do_POST(self) -> None:
            if self.path != "/v1/chat/completions":
                self._send(404, {"error": {"message": f"no route {self.path}"}})
                return
            if not self._authorised():
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            except ValueError as e:
                self._send(400, {"error": {"message": f"bad request: {e}"}})
                return
            try:
                self._send(200, model.chat(body))
            except (KeyError, TypeError, ValueError) as e:
                self._send(400, {"error": {"message": f"bad request: {e}"}})
            except Exception as e:  # e.g. out of GPU memory: the client retries a 500
                self._send(500, {"error": {"message": f"{type(e).__name__}: {e}"}})

        def log_message(self, fmt: str, *args) -> None:
            print(f"{self.address_string()} {fmt % args}", flush=True)

    return Handler


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", required=True, help="model directory")
    ap.add_argument("--served-model-name", required=True)
    ap.add_argument("--kind", choices=("multimodal", "causal"), default="causal")
    ap.add_argument("--dtype", default="bfloat16")
    ap.add_argument("--device-map", default="auto", help="auto spreads the model over the visible GPUs")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, required=True)
    args = ap.parse_args()
    key = os.environ.get("ISOCHRON_SERVER_KEY")
    if not key:
        raise SystemExit("set ISOCHRON_SERVER_KEY")
    print(f"loading {args.model} ({args.kind}, {args.dtype}) with transformers {transformers.__version__}", flush=True)
    model = Model(args.model, args.kind, args.dtype, args.device_map)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(model, args.served_model_name, key))
    print(f"serving {args.served_model_name} on {args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
