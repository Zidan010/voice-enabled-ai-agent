# langchain_groq_rag.py
import os
import json
import faiss
import time
import re
import ast
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from function_agents import WeatherAgent, FinanceAgent

load_dotenv()

# ================================
# GLOBAL CONFIG
# ================================
VECTOR_STORE_DIR = os.getenv("VECTOR_STORE_DIR", "vector_store")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

BASE_MODEL = "llama-3.3-70b-versatile"

if not GROQ_API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY")

if not TAVILY_API_KEY:
    raise RuntimeError("Missing TAVILY_API_KEY (needed for function agents).")

# ================================
# LLM HELPERS
# ================================
def call_llm(system_text: str, user_text: str):
    try:
        llm = ChatGroq(api_key=GROQ_API_KEY, model_name=BASE_MODEL, temperature=0.2)
        resp = llm.invoke([
            SystemMessage(content=system_text),
            HumanMessage(content=user_text)
        ])
        return resp.content
    except:
        return None

# ================================
# CLASSIFIER
# ================================
class QueryClassifier:
    def __init__(self, descriptions: Dict[str, Dict]):
        self.desc = descriptions

    def classify(self, query: str) -> List[str]:
        ql = query.lower()

        # greetings
        if re.search(r"\b(hi|hello|hey|good morning|good evening)\b", ql):
            return ["greeting"]

        # small talk
        if re.search(r"how are you|who are you|what can you do", ql):
            return ["greeting"]

        # OOD heuristic
        bad = ["movie", "recipe", "torrent", "porn", "gossip", "football"]
        if any(x in ql for x in bad):
            return ["unrelated"]

        # LLM classification
        sys = (
            "You classify user queries. "
            "Return ONLY a Python list of relevant agent ids. "
            "If unrelated → ['unrelated'], if greeting → ['greeting']"
        )

        desc_text = "\n".join([f"- {k}: {v['description']}" for k, v in self.desc.items()])
        user = f"Agents:\n{desc_text}\n\nQuery: {query}\nReturn only Python list."

        result = call_llm(sys, user)
        if not result:
            return ["unrelated"]

        try:
            cleaned = result.replace("```", "")
            parsed = ast.literal_eval(cleaned)
            return parsed
        except:
            return ["unrelated"]

# ================================
# UNIFIED SYSTEM
# ================================
class UnifiedAgentSystem:
    def __init__(self, vector_store_dir: str = VECTOR_STORE_DIR):
        self.vector_store_dir = Path(vector_store_dir)

        # registry
        registry_path = self.vector_store_dir / "agent_registry.json"
        with open(registry_path, "r", encoding="utf-8") as f:
            self.registry = json.load(f)

        # embedding model
        emb_name = self.registry["config"]["embedding_model"]
        self.embedding_model = SentenceTransformer(emb_name)

        # document agents
        self.document_agents = list(self.registry["agents"].keys())

        # function agents
        self.weather_agent = WeatherAgent(TAVILY_API_KEY)
        self.finance_agent = FinanceAgent(TAVILY_API_KEY)

        # descriptions
        self.agent_descriptions = {}
        for aid, info in self.registry["agents"].items():
            self.agent_descriptions[aid] = {
                "description": info.get("description", "")
            }

        self.agent_descriptions["Weather_Agent"] = {
            "description": self.weather_agent.description
        }
        self.agent_descriptions["Finance_Agent"] = {
            "description": self.finance_agent.description
        }

        # classifier
        self.classifier = QueryClassifier(self.agent_descriptions)

        # cache
        self._index_cache = {}
        self._metadata_cache = {}

    # --------------------------------
    # LOADING INDEX
    # --------------------------------
    def _load_index(self, agent_id: str):
        if agent_id in self._index_cache:
            return self._index_cache[agent_id], self._metadata_cache[agent_id]

        info = self.registry["agents"][agent_id]
        index_path = self.vector_store_dir / info["index_path"]
        metadata_path = self.vector_store_dir / info["metadata_path"]

        idx = faiss.read_index(str(index_path))
        with open(metadata_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self._index_cache[agent_id] = idx
        self._metadata_cache[agent_id] = meta
        return idx, meta

    # --------------------------------
    # RETRIEVAL
    # --------------------------------
    def _retrieve(self, agent_id: str, query: str, k: int = 2):
        idx, meta = self._load_index(agent_id)
        q_emb = self.embedding_model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        scores, indices = idx.search(np.asarray(q_emb, dtype="float32"), k)

        results = []
        for s, i in zip(scores[0], indices[0]):
            if i < len(meta["chunks"]):
                chunk = meta["chunks"][i]
                results.append({
                    "score": float(s),
                    "content": chunk["content"],
                    "section_path": chunk.get("section_path", []),
                })
        return results

    # --------------------------------
    # FUNCTION AGENTS
    # --------------------------------
    def _exec_function_agent(self, agent_id: str, query: str) -> str:
        if agent_id == "Weather_Agent":
            m = re.search(r"in\s+([A-Za-z ]+)", query)
            loc = m.group(1) if m else "Dhaka"
            return self.weather_agent.execute(loc)

        if agent_id == "Finance_Agent":
            m = re.search(r"\b[A-Z]{1,5}\b", query.upper())
            ticker = m.group(0) if m else "market"
            return self.finance_agent.execute(ticker)

        return "Unknown function agent."

    # --------------------------------
    # MAIN PIPELINE
    # --------------------------------
    def query(self, user_query: str, verbose: bool = False) -> Dict:
        start = time.time()

        # classification
        cls = self.classifier.classify(user_query)

        # greeting
        if cls == ["greeting"]:
            text = call_llm(
                "You reply politely to greetings.",
                user_query
            )
            return {
                "routing": {"agents": ["greeting"], "reasoning": "Greeting detected"},
                "response": text,
                "metrics": {}
            }

        # unrelated
        if cls == ["unrelated"]:
            refuse = (
                "Sorry, that is outside my domains. "
                "I handle AI, Cybersecurity, Digital Health, Human Development, Renewable Energy, "
                "plus Weather and Finance via real-time search."
            )
            return {
                "routing": {"agents": ["unrelated"], "reasoning": "Out-of-domain"},
                "response": refuse,
                "metrics": {}
            }

        # real agents
        results = {}
        for aid in cls:
            if aid in self.document_agents:
                results[aid] = {
                    "type": "document",
                    "chunks": self._retrieve(aid, user_query)
                }
            elif aid in ["Weather_Agent", "Finance_Agent"]:
                results[aid] = {
                    "type": "function",
                    "response": self._exec_function_agent(aid, user_query)
                }

        # build context
        ctx = ""
        for aid, r in results.items():
            if r["type"] == "document":
                ctx += f"\n=== {aid} ===\n"
                for c in r["chunks"]:
                    ctx += f"[score={c['score']:.4f}] {c['content']}\n\n"
            else:
                ctx += f"\n=== {aid} (real-time) ===\n{r['response']}\n"

        # final answer
        answer = call_llm(
            "You answer using provided context. If context missing, say so.",
            f"Context:\n{ctx}\n\nQuestion:{user_query}"
        )

        end = time.time()

        return {
            "routing": {"agents": cls, "reasoning": "Classifier-selected"},
            "context": ctx,
            "response": answer,
            "metrics": {"total_time": end - start}
        }
