"""
Genomics Literature Review Agent
Fork lineage: nicknochnack/WatsonxCrewAI -> L1k1th1508/ai-agent -> this.

Original repo built a keynote-writing crew. This keeps the CrewAI
orchestration pattern but replaces the task entirely: three agents search,
analyze, and synthesize PubMed literature into a structured review on a
topic you provide (gene, variant, disease, pathway, etc).
"""

import os

from crewai import LLM, Agent, Crew, Process, Task

from pubmed_tool import pubmed_search

# ---------------------------------------------------------------------------
# LLM setup — local model via Ollama.
#
# Prerequisites:
#   1. Install Ollama: https://ollama.com/download
#   2. Pull a model with enough context/reasoning for multi-step synthesis:
#        ollama pull llama3.1        (8B — fast, weaker synthesis quality)
#        ollama pull qwen2.5:14b     (better instruction-following, needs ~16GB RAM)
#      A general-purpose chat model is fine — you don't need anything
#      "medical" or "bio" specific; the domain knowledge lives in the
#      PubMed abstracts the tool retrieves, not in the model's training data.
#   3. Make sure `ollama serve` is running (it usually auto-starts).
#
# Set OLLAMA_MODEL to whatever you pulled, or leave the default below.
# ---------------------------------------------------------------------------
llm = LLM(
    model=f"ollama/{os.getenv('OLLAMA_MODEL', 'qwen2.5:14b')}",
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    temperature=0.2,
)

# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------
literature_scout = Agent(
    role="Genomics Literature Scout",
    goal="Find the most relevant, credible PubMed papers on the given topic",
    backstory=(
        "A research librarian specializing in genomics and molecular biology. "
        "Knows how to construct precise PubMed queries (gene names, variant "
        "nomenclature, MeSH-adjacent terms) to surface primary research over "
        "reviews unless reviews are explicitly requested."
    ),
    tools=[pubmed_search],
    llm=llm,
    verbose=True,
)

findings_analyst = Agent(
    role="Findings Analyst",
    goal="Extract the concrete claims, methods, and results from each paper",
    backstory=(
        "A genomics postdoc who reads papers for a living. For each paper, "
        "pulls out: the specific question asked, methodology (cohort size, "
        "sequencing/assay type, statistical approach), the actual result "
        "with numbers where available, and stated limitations. Flags when "
        "a paper's claims are preliminary, underpowered, or contradicted "
        "elsewhere in the set."
    ),
    llm=llm,
    verbose=True,
)

synthesis_writer = Agent(
    role="Synthesis Writer",
    goal="Turn the analyzed findings into a structured, citable literature review",
    backstory=(
        "A scientific writer who organizes findings by theme rather than "
        "paper-by-paper, explicitly calls out where the literature agrees, "
        "where it conflicts, and what's still an open question. Every claim "
        "is attributed to a PMID. Never states a finding without a citation."
    ),
    llm=llm,
    verbose=True,
)

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------
search_task = Task(
    description=(
        "Search PubMed for papers on: {topic}\n"
        "Retrieve at least 10-15 relevant papers, prioritizing recent "
        "primary research. If the initial query returns few or irrelevant "
        "results, refine the query (try synonyms, gene aliases, narrower "
        "or broader terms) and search again."
    ),
    expected_output="A list of papers with PMID, title, authors, year, journal, and abstract.",
    agent=literature_scout,
)

analysis_task = Task(
    description=(
        "For each paper found, extract: (1) the specific research question, "
        "(2) methodology and sample/cohort size, (3) key quantitative "
        "results, (4) stated limitations. Note any papers that contradict "
        "each other."
    ),
    expected_output="A structured breakdown of findings per paper, with PMIDs preserved.",
    agent=findings_analyst,
    context=[search_task],
)

synthesis_task = Task(
    description=(
        "Write a literature review on '{topic}' organized by theme (not "
        "paper-by-paper). Structure it as:\n"
        "1. Overview (2-3 sentences on the state of the field)\n"
        "2. Key findings by theme, each claim cited with (PMID: xxxxxxx)\n"
        "3. Areas of consensus\n"
        "4. Contradictions or unresolved questions in the literature\n"
        "5. Gaps / suggested directions for further research\n"
        "6. Full reference list (PMID + title + year + link)\n"
        "Do not state any claim without a PMID citation."
    ),
    expected_output="A complete markdown literature review document.",
    agent=synthesis_writer,
    context=[search_task, analysis_task],
    output_file=f"outputs/{{topic_slug}}_review.md",
)

crew = Crew(
    agents=[literature_scout, findings_analyst, synthesis_writer],
    tasks=[search_task, analysis_task, synthesis_task],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    topic = input("Genomics research topic (gene, variant, disease, pathway, etc.): ").strip()
    topic_slug = "".join(c if c.isalnum() else "_" for c in topic.lower())[:50]

    result = crew.kickoff(inputs={"topic": topic, "topic_slug": topic_slug})

    print(f"\n{'=' * 60}\nReview complete. Saved to outputs/{topic_slug}_review.md\n{'=' * 60}\n")
    print(result)