import hashlib
import re
import time
from typing import Any, Dict, List, Optional

import numpy as np
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from config import settings
from document_loader import PropertyDocumentLoader
from llm_client import call_llm
from market_data import market_data

INVESTOR_STYLE = {
    "individual": "Individual investor: plain language, focus on net yield and total cost of ownership.",
    "wealth_advisor": "Wealth advisor preparing a brief for an HNI client: concise, client-ready, flag diversification and tax points.",
    "relocation": "Relocation/migration firm: emphasise residency or visa links, ownership rules for foreigners and repatriation of funds.",
}
RISK_STYLE = {
    "conservative": "conservative: favour stability, liquidity and ready property over growth.",
    "moderate": "moderate: balance yield and appreciation.",
    "aggressive": "aggressive: growth-focused, accepts off-plan and volatility.",
}

BASE_RULES = """You are a Global Property Investment Analyst serving individual investors ($200K-$2M), independent wealth advisors advising HNIs, and cross-border relocation firms.

RULES:
- Use ONLY the CONTEXT and LIVE MARKET DATA below. If data is missing or thin, say so in one line (e.g. "Limited rental data for this area").
- LIVE MARKET DATA comes from open APIs (World Bank, BIS, currency-api) and carries a year or date. Use it for inflation, GDP, interest-rate, population, house-price-index and currency facts, and cite the source and year, e.g. "(World Bank, 2025)". It is country-level, so say so when applying it to a city. Each line starts with its market name: attribute a figure ONLY to that market, never move a figure from one market to another, and say \"not available\" when a line says so. If it conflicts with an older figure in the CONTEXT for the same metric, prefer the live figure and note the difference in one line. Flag any live figure older than 18 months. It has NO rents, yields or prices per sqm; those come only from the CONTEXT.
- If the user asks about a market that is not in AVAILABLE MARKETS, say there is no data for it, name the markets you do have, and do not guess figures.
- State data freshness only if the context gives a date; otherwise write "Data date not specified in sources". Flag data older than 18 months.
- Never give personalized financial advice; say "This requires a licensed advisor review" if asked what to buy.
- Never project returns with false precision; use ranges.
- Tax and regulatory points are "indicative only". If the property currency differs from the user's (e.g. USD), add a one-line currency volatility warning.
- Tone: analytical, not salesy. Add a short "why it matters" to key metrics.
- Tailor the analysis to the USER PROFILE when one is given. Do not ask for anything already in it."""

CHAT_FORMAT = """CLARIFYING QUESTIONS:
Ask only about details that materially change the answer and are not already in the USER PROFILE or anywhere in the conversation. You may ask at any point, including on follow-up questions. Typical gaps: target market (one of AVAILABLE MARKETS, or compare several), property type (Residential / Commercial), holding period (Under 3 years / 3-7 years / 7+ years), main goal (Rental income / Capital growth / Balanced).
- Ask 1-3 questions covering what is missing. Never repeat a question the user has already answered, and skip anything they already stated.
- If nothing material is missing, or the user's latest message answers your questions, give the full analysis instead of asking more.
- Every question MUST have 2-4 short options after "|". Reply with EXACTLY this format and nothing else, for example:
CLARIFY:
Q: Which market should I focus on? | {market_options}
Q: Which property type? | Residential | Commercial
Q: What is your holding period? | Under 3 years | 3-7 years | 7+ years

FULL ANALYSIS FORMAT (about 200 words, never more than 220, specific figures from the CONTEXT, no filler). Each part has up to 3 short bullet lines starting with "-":
**1. Market Context**
**2. Price Comparison**
**3. Rental Yield** (gross vs net, vacancy)
**4. Cost of Capital** (buying, holding, selling costs)
**5. Risk Flags**
**Bottom line**
Write 2-3 sentences tailored to the USER PROFILE and the user's answers, say what to verify next, and note this is indicative and needs a licensed advisor review."""

COMPARE_FORMAT = """TASK: compare the requested metric across the requested regions using only the CONTEXT.
FORMAT (150 words max, no filler):
- One line per region with the key figures for the metric.
- Verdict: 2 lines on which looks stronger for this profile and why it matters.
- Data gaps / risk flags: 1-2 lines.
Do not ask clarifying questions."""


class PropertyInvestmentRAG:
    """RAG system: local TF-IDF retrieval + a pluggable LLM for answer generation."""

    def __init__(self):
        self.loader = PropertyDocumentLoader()
        self.documents: List[Document] = []
        self.split_documents: List[Document] = []
        self.documents_by_region: Dict[str, List[Document]] = {}
        self.documents_by_type: Dict[str, List[Document]] = {}
        self.region_indices: Dict[str, np.ndarray] = {}
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.doc_matrix = None
        self.data_version = ""
        self._initialize()

    def _initialize(self):
        print("=" * 60)
        print("Initializing Property Investment RAG System")
        print("=" * 60)

        self.documents_by_region, self.documents_by_type = {}, {}
        self.region_indices, self.vectorizer, self.doc_matrix = {}, None, None

        self.documents = self.loader.load_all_documents()
        if not self.documents:
            print("⚠️  Warning: No documents loaded.")
            self.split_documents = []
            return

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""],
        )
        self.split_documents = splitter.split_documents(self.documents)
        print(f"✓ Documents split into {len(self.split_documents)} chunks")

        indices: Dict[str, List[int]] = {}
        for i, doc in enumerate(self.split_documents):
            region = doc.metadata.get("region", "Unknown")
            doc_type = doc.metadata.get("document_type", "Unknown")
            self.documents_by_region.setdefault(region, []).append(doc)
            self.documents_by_type.setdefault(doc_type, []).append(doc)
            indices.setdefault(region, []).append(i)
        self.region_indices = {r: np.array(ix) for r, ix in indices.items()}

        files = sorted({(d.metadata.get("region", ""), d.metadata.get("file_name", "")) for d in self.split_documents})
        self.data_version = hashlib.md5(
            (f"{len(self.split_documents)}|" + "|".join(f"{r}/{f}" for r, f in files)).encode()
        ).hexdigest()[:12]

        self.vectorizer = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), max_features=200000, sublinear_tf=True
        )
        self.doc_matrix = self.vectorizer.fit_transform([d.page_content for d in self.split_documents])
        print(f"✓ Indexed {self.doc_matrix.shape[0]} chunks across {len(self.documents_by_region)} regions")
        market_data.refresh_async(self.regions)
        print("=" * 60)

    # ---------- retrieval ----------
    def retrieve(self, query: str, k: int = 5, region: Optional[str] = None) -> List[Document]:
        if self.vectorizer is None or not query.strip():
            return []
        sims = linear_kernel(self.vectorizer.transform([query]), self.doc_matrix)[0]
        if region is not None:
            idx = self.region_indices.get(region)
            if idx is None or len(idx) == 0:
                return []
            order = idx[np.argsort(sims[idx])[::-1][:k]]
        else:
            order = np.argsort(sims)[::-1][:k]
        return [self.split_documents[i] for i in order if sims[i] > 0]

    @property
    def regions(self) -> List[str]:
        return sorted(self.region_indices)

    def _markets_block(self) -> str:
        return "AVAILABLE MARKETS (the only markets with data): " + (", ".join(self.regions) or "none loaded")

    def _chat_format(self) -> str:
        options = " | ".join((self.regions[:3] or ["Market A", "Market B"]) + ["Compare several"])
        return CHAT_FORMAT.replace("{market_options}", options)

    def _without_regions(self, text: str) -> str:
        """Drop market names from a query that is already restricted to a market, so page headers don't dominate."""
        stripped = text
        for region in self.regions:
            stripped = re.sub(re.escape(region), " ", stripped, flags=re.IGNORECASE)
        stripped = " ".join(stripped.split())
        return stripped if len(stripped) > 3 else text

    @staticmethod
    def _live_block(live_text: str) -> str:
        if not live_text:
            return "LIVE MARKET DATA: not available right now."
        return "LIVE MARKET DATA (open APIs):\n" + live_text

    @staticmethod
    def _regions_of(docs: List[Document], limit: int = 3) -> List[str]:
        seen: List[str] = []
        for d in docs:
            r = d.metadata.get("region")
            if r and r not in seen:
                seen.append(r)
        return seen[:limit]

    def _known_facts(self, user_text: str) -> str:
        """Details the user has already given anywhere in the conversation, so the AI never asks for them again."""
        t = user_text.lower()
        facts = []
        markets = self._mentioned_regions(user_text)
        if markets:
            facts.append("target market: " + ", ".join(markets))
        horizon = re.search(r"\d+(?:\s*-\s*\d+)?\+?\s*-?\s*(?:years?|yrs?)\b", t)
        if horizon:
            facts.append(f"holding period: {horizon.group(0).strip()}")
        if re.search(r"\b(residential|apartments?|villas?|studios?|townhouses?|flats?)\b", t):
            facts.append("property type: residential")
        elif re.search(r"\b(commercial|offices?|retail|warehouses?)\b", t):
            facts.append("property type: commercial")
        if re.search(r"rental income|rental yield|\byields?\b|cash ?flow|passive income", t):
            facts.append("goal: rental income")
        elif re.search(r"capital growth|appreciation|capital gains?", t):
            facts.append("goal: capital growth")
        if not facts:
            return ""
        return "ALREADY KNOWN FROM THE CONVERSATION (never ask about these again):\n" + "\n".join(f"- {f}" for f in facts)

    def _mentioned_regions(self, text: str) -> List[str]:
        lowered = text.lower()
        return [r for r in self.regions if r.lower() in lowered]

    @staticmethod
    def _sources(docs: List[Document]) -> List[Dict[str, str]]:
        seen, out = set(), []
        for doc in docs:
            key = (doc.metadata.get("file_name"), doc.metadata.get("page_number"))
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "file": str(doc.metadata.get("file_name", "Unknown")),
                "region": str(doc.metadata.get("region", "Unknown")),
                "type": str(doc.metadata.get("document_type", "Unknown")),
                "preview": doc.page_content[:200] + "...",
            })
        return out

    @staticmethod
    def _context(docs: List[Document], limit: int = 6, chars: int = 600) -> str:
        return "\n---\n".join(
            f"[{d.metadata.get('region', '?')} | {d.metadata.get('file_name', '?')}]\n{d.page_content[:chars]}"
            for d in docs[:limit]
        )

    @staticmethod
    def _profile_block(profile: Optional[Dict[str, Any]]) -> str:
        if not profile:
            return "USER PROFILE: none provided."
        lines = ["USER PROFILE (given by the user, treat as fact, never ask for it again):"]
        if profile.get("type") in INVESTOR_STYLE:
            lines.append(f"- {INVESTOR_STYLE[profile['type']]}")
        if profile.get("budget"):
            lines.append(f"- Budget: ${float(profile['budget']):,.0f} USD")
        if profile.get("risk_profile") in RISK_STYLE:
            lines.append(f"- Risk profile: {RISK_STYLE[profile['risk_profile']]}")
        return "\n".join(lines)

    @staticmethod
    def _parse_clarify(answer: str) -> Optional[List[Dict[str, Any]]]:
        if not answer.lstrip().upper().startswith("CLARIFY"):
            return None
        body = answer.lstrip()[len("CLARIFY"):].lstrip(": \n")
        questions = []
        for line in body.splitlines():
            line = line.strip().lstrip("-*0123456789. ").strip()
            if line[:2].upper() == "Q:":
                line = line[2:]
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if parts and (len(parts) > 1 or parts[0].endswith("?")):
                questions.append({"question": parts[0], "options": parts[1:]})
        return questions[:3] or None

    @staticmethod
    def _drop_known(questions: List[Dict[str, Any]], known: str) -> List[Dict[str, Any]]:
        """Remove questions about details the user has already given."""
        topics = {
            "target market": r"market|city|country|location|where",
            "holding period": r"holding|hold|how long|period|horizon|years",
            "property type": r"property type|type of property|residential|commercial",
            "goal": r"goal|objective|priority|income|growth",
        }
        patterns = [pat for name, pat in topics.items() if name in known]
        return [q for q in questions if not any(re.search(p, q["question"], re.I) for p in patterns)]

    # ---------- generation ----------
    def _generate(self, system: str, messages: List[Dict[str, str]], docs: List[Document],
                  llm_cfg: Optional[Dict[str, Any]], max_tokens: int = 450) -> Dict[str, Any]:
        sources = self._sources(docs)
        if llm_cfg is None:
            return {
                "answer": "No LLM is configured, so I can only show matching excerpts below. "
                          "An admin can add an API key in the Status tab.\n\n"
                          + (self._context(docs, limit=2, chars=400) or "No matching documents found."),
                "sources": sources, "success": True, "usage": None, "llm": None,
            }
        try:
            answer, usage = call_llm(llm_cfg, system, messages, max_tokens=max_tokens)
        except Exception as e:
            return {"answer": f"LLM error ({llm_cfg['name']}): {e}", "sources": sources,
                    "success": False, "usage": None, "llm": llm_cfg["name"]}
        return {"answer": answer, "sources": sources, "success": True, "usage": usage, "llm": llm_cfg["name"]}

    def chat(self, messages: List[Dict[str, str]], profile: Optional[Dict[str, Any]] = None,
             llm_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.split_documents:
            return {"answer": "No documents loaded. Please ensure property data exists.",
                    "sources": [], "success": False, "usage": None, "llm": None}

        recent = messages[-8:]
        user_turns = [m["content"] for m in recent if m["role"] == "user"]
        query_text = " ".join(user_turns[-3:])
        mentioned = self._mentioned_regions(query_text)
        if mentioned:
            per_region = max(2, settings.RETRIEVAL_K // len(mentioned))
            topic = self._without_regions(query_text)
            docs = [d for r in mentioned for d in self.retrieve(topic, k=per_region, region=r)]
        else:
            docs = self.retrieve(query_text, k=settings.RETRIEVAL_K)

        live_regions = mentioned or self._regions_of(docs)
        live_text, live_sources = market_data.context_for(live_regions)

        system = "\n\n".join([
            BASE_RULES, self._chat_format(), self._markets_block(), self._profile_block(profile),
            self._known_facts(" ".join(user_turns)),
            self._live_block(live_text),
            "CONTEXT:\n" + (self._context(docs) or "No relevant documents found."),
        ])
        time.sleep(0.3)
        result = self._generate(system, recent, docs, llm_cfg, max_tokens=500)
        result["sources"] = result["sources"] + live_sources
        questions = self._parse_clarify(result["answer"]) if result["success"] else None
        if questions:
            kept = self._drop_known(questions, self._known_facts(" ".join(user_turns)))
            if kept:
                questions = kept
            else:
                first_usage = result["usage"]
                full_format = self._chat_format()
                analysis_only = (
                    "Do NOT ask any questions. State any assumption in one line and give the full analysis now.\n\n"
                    + full_format[full_format.index("FULL ANALYSIS FORMAT"):]
                )
                result = self._generate(system.replace(full_format, analysis_only), recent, docs, llm_cfg, max_tokens=500)
                result["sources"] = result["sources"] + live_sources
                if first_usage and result.get("usage"):
                    result["usage"] = {k: first_usage[k] + result["usage"][k] for k in first_usage}
                questions = None
        if questions:
            result["clarifying_questions"] = questions
            numbered = "\n".join(f"{i}. {q['question']}" for i, q in enumerate(questions, 1))
            result["answer"] = "To tailor this to you, I need a few details:\n" + numbered
        return result

    def compare_regions(self, metric: str, regions: List[str], profile: Optional[Dict[str, Any]] = None,
                        llm_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.split_documents:
            return {"answer": "No documents loaded.", "sources": [], "success": False, "usage": None, "llm": None}

        docs: List[Document] = []
        per_region = 3 if len(regions) <= 3 else 2
        for region in regions:
            docs.extend(self.retrieve(self._without_regions(metric), k=per_region, region=region))

        live_text, live_sources = market_data.context_for(regions)
        system = "\n\n".join([
            BASE_RULES, COMPARE_FORMAT, self._markets_block(), self._profile_block(profile),
            self._live_block(live_text),
            "CONTEXT:\n" + (self._context(docs, limit=min(per_region * len(regions), 12)) or "No relevant documents found."),
        ])
        question = f"Compare {metric} across: {', '.join(regions)}."
        result = self._generate(system, [{"role": "user", "content": question}], docs, llm_cfg)
        result["sources"] = result["sources"] + live_sources
        return result

    # ---------- admin ----------
    def get_system_stats(self) -> Dict[str, Any]:
        return self.loader.get_statistics()

    def reload_documents(self):
        print("🔄 Reloading documents...")
        self._initialize()
        return self.get_system_stats()
