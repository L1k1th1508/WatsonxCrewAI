# Genomics Literature Review Agent

Fork lineage: `nicknochnack/WatsonxCrewAI` → `L1k1th1508/ai-agent` (keynote writer) → this (literature review agent).

## What changed from the original repo

| Original | This version |
|---|---|
| Task: write a keynote deck | Task: synthesize a genomics literature review |
| Search tool: Serper (generic Google search) | Search tool: NCBI PubMed E-utilities (direct abstract retrieval, no key needed) |
| 1 agent | 3 agents: Literature Scout → Findings Analyst → Synthesis Writer |
| Single-pass generation | Sequential pipeline with each stage's output feeding the next |

The CrewAI + watsonx.ai orchestration pattern is the only thing kept as-is.

## Setup

```bash
git clone <this repo>
cd genomics-lit-agent
pip install -r requirements.txt
```

Install [Ollama](https://ollama.com/download) and pull a model:

```bash
ollama pull llama3.1        # 8B, fast, weaker synthesis quality
# or
ollama pull qwen2.5:14b     # better instruction-following, ~16GB RAM
```

Make sure `ollama serve` is running (it usually auto-starts after install).

Optional environment variables:

```bash
export OLLAMA_MODEL="llama3.1"              # defaults to llama3.1 if unset
export OLLAMA_BASE_URL="http://localhost:11434"  # defaults to this if unset

# Optional — raises PubMed rate limit from 3 req/sec to 10 req/sec:
export NCBI_API_KEY="your-ncbi-api-key"
```

Run:

```bash
python agent.py
```

You'll be prompted for a topic — a gene, variant, disease, or pathway (e.g. `"TP53 germline variants and Li-Fraumeni syndrome"`). Output is saved to `outputs/<topic>_review.md`.

## Using a different LLM

The Ollama block in `agent.py` is isolated at the top of the file. CrewAI's `LLM` class wraps LiteLLM, so swapping providers is usually a one-line model string change, e.g.:

```python
llm = LLM(model="gpt-4o", api_key=os.environ["OPENAI_API_KEY"])
llm = LLM(model="claude-sonnet-4-5-20250929", api_key=os.environ["ANTHROPIC_API_KEY"])
```

See [LiteLLM's provider list](https://docs.litellm.ai/docs/providers) for exact model string formats.

## Known limitations — read before relying on this for actual research

- **[Certain]** The PubMed tool searches abstracts only, not full text. Key methodology or caveats buried in the full paper won't be seen.
- **[Certain]** This has not been run end-to-end against live PubMed or a live watsonx.ai endpoint in this environment (network sandbox only allowlists package registries, not `eutils.ncbi.nlm.nih.gov` or IBM's API). Syntax has been verified; behavior has not. Run a small test topic first and check the output against the actual abstracts before trusting it.
- **[Certain]** LLMs hallucinate citations. Every PMID in the output should be spot-checked against pubmed.ncbi.nlm.nih.gov before you cite it anywhere real. Treat this as a first-pass draft that accelerates reading, not a substitute for reading.
- **[Likely]** Local 7-14B models are noticeably weaker than frontier hosted models at the synthesis step specifically — following the "cite every claim with a PMID, never invent one" instruction reliably. Check the synthesis output against the analysis-stage output (not just against PubMed) to catch citations that got reassigned to the wrong paper.
- **[Likely]** For a systematic review (as opposed to a scoping/narrative one), this pipeline is not sufficient — it doesn't do PRISMA-style screening, doesn't deduplicate across databases, and doesn't assess study quality/risk of bias. Don't submit its output as a systematic review methodology.
