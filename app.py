import streamlit as st
from pathlib import Path

from core.gemini import gemini_available
from core.database import (
    initialize_database,
    create_research_run,
    save_source,
    save_claims,
    save_analysis,
    get_recent_runs
)
from modules.extractor import extract_sources, discover_sources
from modules.analyzer import analyze_sources
from modules.evidence import (
    build_evidence_map,
    validate_contradictions,
    build_source_network
)
from modules.scoring import score_all_gaps, get_priority_counts
from modules.verification import (
    build_verification_checklist,
    checklist_summary,
    update_checklist_status
)
from components.visualizations import (
    render_evidence_network,
    render_gap_chart
)


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="GapMind AI | Research Intelligence",
    page_icon="👑",
    layout="wide"
)

BASE_DIR = Path(__file__).parent
CSS_PATH = BASE_DIR / "assets" / "style.css"

if CSS_PATH.exists():
    st.html(
        f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>"
    )

initialize_database()


# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

defaults = {
    "analysis": None,
    "sources": [],
    "limited_sources": [],
    "topic": "",
    "evidence_map": [],
    "scored_gaps": [],
    "checklist": [],
    "run_id": None,
    "current_page": "Research Workspace"
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def html(content):
    st.html(content)


def heading(title, subtitle):
    html(f"""
    <div class="page-heading">
        <div class="eyebrow">GAPMIND AI / RESEARCH INTELLIGENCE</div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    """)


def metric_card(label, value, detail, symbol):
    html(f"""
    <div class="metric-card">
        <div style="display:flex;justify-content:space-between;">
            <div class="metric-label">{label}</div>
            <div style="font-size:24px;color:#ed5969;">{symbol}</div>
        </div>
        <div class="metric-value">{value}</div>
        <div class="metric-detail">{detail}</div>
    </div>
    """)


def empty_state(title, message):
    html(f"""
    <div class="empty-state">
        <div class="empty-icon">◈</div>
        <h3>{title}</h3>
        <p>{message}</p>
    </div>
    """)


def render_brand():
    html("""
    <div class="topbar">
        <div class="brand">
            <div class="brand-icon">♛</div>
            <div>
                <div class="brand-name">GAPMIND <span>AI</span></div>
                <div class="brand-subtitle">
                    CLAIM-LEVEL EVIDENCE INTELLIGENCE
                </div>
            </div>
        </div>
        <div class="system-status">
            <span class="status-dot"></span>
            SYSTEM READY
        </div>
    </div>
    """)


def render_research_summary(summary, sources):
    """
    Render Gemini's summary as readable cards.
    Supports both a list of findings and a plain text summary.
    """

    if not summary:
        st.info("No research summary available.")
        return

    source_lookup = {
        source.get("source_id"): source
        for source in sources
    }

    if isinstance(summary, str):
        st.markdown(summary)
        return

    if isinstance(summary, dict):
        summary = [summary]

    if not isinstance(summary, list):
        st.write(summary)
        return

    for index, item in enumerate(summary, 1):

        if isinstance(item, str):
            point = item
            source_ids = []

        elif isinstance(item, dict):
            point = (
                item.get("point")
                or item.get("summary")
                or item.get("finding")
                or item.get("text")
                or str(item)
            )
            source_ids = item.get("source_ids", [])

        else:
            point = str(item)
            source_ids = []

        with st.container(border=True):
            st.markdown(f"**Finding {index}**")
            st.write(point)

            if source_ids:
                st.caption("Supporting sources")

                for source_id in source_ids:
                    source = source_lookup.get(source_id)

                    if source:
                        title = source.get(
                            "title",
                            f"Source {source_id}"
                        )
                        url = source.get("url")

                        if url:
                            st.markdown(
                                f"- [Source {source_id}: {title}]({url})"
                            )
                        else:
                            st.write(
                                f"- Source {source_id}: {title}"
                            )
                    else:
                        st.write(f"- Source {source_id}")


def navigate(page):
    st.session_state.current_page = page
    st.rerun()


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

pages = [
    "Research Workspace",
    "Evidence Intelligence",
    "Information Gaps",
    "Verification Center",
    "Research History"
]

with st.sidebar:

    html("""
    <div style="text-align:center;padding:15px 0 25px;">
        <div style="color:#ed3445;font-size:46px;">♛</div>
        <div style="font-size:22px;font-weight:900;color:white;">
            GAPMIND <span style="color:#ed3445;">AI</span>
        </div>
        <div style="color:#a69a9e;font-size:9px;letter-spacing:2px;">
            INTELLIGENCE PLATFORM
        </div>
    </div>
    """)

    st.markdown("---")

    page = st.radio(
        "Navigation",
        pages,
        index=pages.index(st.session_state.current_page),
        label_visibility="collapsed"
    )

    st.session_state.current_page = page

    st.markdown("---")

    if gemini_available():
        st.success("Gemini Connected")
    else:
        st.error("Gemini API Key Missing")

    st.caption("GAPMIND AI • HACKATHON EDITION")


# --------------------------------------------------
# AUTOMATIC RESEARCH ANALYSIS ENGINE
# --------------------------------------------------

def run_research(
    topic,
    urls=None,
    uploaded_files=None,
    pasted_text=None
):

    if not topic.strip():
        st.error("Please enter a research topic.")
        return

    if not gemini_available():
        st.error("Gemini API key is missing. Check your .env file.")
        return

    collected_sources = []
    limited_sources = []
    errors = []

    with st.spinner("Discovering relevant sources across the web..."):

        discovered, limited, search_errors = discover_sources(
            topic,
            max_results=3
        )

        collected_sources.extend(discovered)
        limited_sources.extend(limited)
        errors.extend(search_errors)

    if urls or uploaded_files or pasted_text:

        with st.spinner("Collecting your additional sources..."):

            additional, extraction_errors = extract_sources(
                urls=urls,
                uploaded_files=uploaded_files,
                pasted_text=pasted_text
            )

            errors.extend(extraction_errors)

            existing_urls = {
                source.get("url")
                for source in collected_sources
                if source.get("url")
            }

            for source in additional:
                source_url = source.get("url")

                if source_url and source_url in existing_urls:
                    continue

                collected_sources.append(source)

                if source_url:
                    existing_urls.add(source_url)

            # Remove limited entries if the same URL was
            # successfully extracted through a manual source.
            readable_urls = {
                source.get("url")
                for source in collected_sources
                if source.get("url")
            }

            limited_sources = [
                source
                for source in limited_sources
                if source.get("url") not in readable_urls
            ]

    st.session_state.limited_sources = limited_sources

    for error in errors:
        st.warning(error)

    if not collected_sources:

        if limited_sources:
            st.warning(
                "No complete readable documents were collected. "
                "Search previews are available below, but they will "
                "not be treated as full research evidence."
            )
        else:
            st.error(
                "GapMind could not collect readable sources. "
                "Try another topic or add a URL/PDF manually."
            )

        return

    st.info(
        f"GapMind collected {len(collected_sources)} readable sources. "
        "Starting evidence analysis..."
    )

    try:

        with st.spinner(
            "Gemini is analysing claims, gaps and contradictions..."
        ):

            for index, source in enumerate(collected_sources, 1):
                source["source_id"] = index

            result = analyze_sources(topic, collected_sources)

            evidence = build_evidence_map(
                result,
                collected_sources
            )

            contradictions = validate_contradictions(
                result,
                collected_sources
            )

            scored = score_all_gaps(
                result.get("gaps", []),
                len(collected_sources)
            )

            verification = build_verification_checklist(
                result,
                scored
            )

            run_id = create_research_run(topic)

            database_claims = []

            for source in collected_sources:
                source["database_id"] = save_source(
                    run_id,
                    source
                )

            for claim in result.get("claims", []):

                for source_id in claim.get("source_ids", []):

                    source_index = source_id - 1

                    if 0 <= source_index < len(collected_sources):

                        database_claims.append({
                            "source_id": collected_sources[
                                source_index
                            ]["database_id"],
                            "claim_text": claim.get(
                                "claim_text", ""
                            ),
                            "claim_type": claim.get(
                                "claim_type", "statement"
                            ),
                            "confidence": claim.get(
                                "confidence", "unassessed"
                            )
                        })

            if database_claims:
                save_claims(run_id, database_claims)

            result["contradictions"] = contradictions

            save_analysis(run_id, result)

            st.session_state.topic = topic
            st.session_state.sources = collected_sources
            st.session_state.limited_sources = limited_sources
            st.session_state.analysis = result
            st.session_state.evidence_map = evidence
            st.session_state.scored_gaps = scored
            st.session_state.checklist = verification
            st.session_state.run_id = run_id

        st.success("Research analysis completed successfully!")
        st.rerun()

    except Exception as error:
        st.error(f"Research analysis failed: {error}")


# --------------------------------------------------
# SHARED DATA
# --------------------------------------------------

analysis = st.session_state.analysis
sources = st.session_state.sources
limited_sources = st.session_state.limited_sources
evidence_map = st.session_state.evidence_map
gaps = st.session_state.scored_gaps
checklist = st.session_state.checklist


# --------------------------------------------------
# RESEARCH WORKSPACE
# --------------------------------------------------

if page == "Research Workspace":

    render_brand()

    html("""
    <div style="
        padding:30px;
        margin:15px 0 25px;
        border-radius:16px;
        border:1px solid rgba(190,75,90,.25);
        background:linear-gradient(120deg,#171013,#0c090a);
    ">
        <div style="color:#d96a78;font-size:10px;font-weight:800;
                    letter-spacing:2px;margin-bottom:12px;">
            GAPMIND AI / RESEARCH INTELLIGENCE
        </div>
        <div style="color:white;font-size:clamp(30px,4vw,46px);
                    font-weight:900;line-height:1.15;">
            Research Smarter.<br>
            <span style="color:#e65a69;">Find What Matters.</span>
        </div>
        <div style="color:#b9aaae;font-size:13px;margin-top:13px;">
            Discover what your sources reveal — and what they leave unanswered.
        </div>
    </div>
    """)

    verified_count = (
        checklist_summary(checklist)["verified"]
        if checklist else 0
    )

    columns = st.columns(4)

    metrics = [
        ("SOURCES", len(sources), "Documents analysed", "▤"),
        ("CLAIMS", len(evidence_map), "Source-linked claims", "◎"),
        ("GAPS FOUND", len(gaps), "Potential information gaps", "⚠"),
        ("VERIFIED TASKS", verified_count, "Completed tasks", "✓")
    ]

    for col, item in zip(columns, metrics):
        with col:
            metric_card(*item)

    st.write("")

    left, right = st.columns(2)

    with left:
        st.markdown("### Evidence Network")

        if evidence_map:
            render_evidence_network(
                build_source_network(evidence_map)
            )
        else:
            st.caption(
                "Your evidence network will appear after analysis."
            )

    with right:
        st.markdown("### Information Gaps")

        if gaps:
            render_gap_chart(gaps)
        else:
            st.caption(
                "Your gap ranking will appear after analysis."
            )

    st.markdown("---")

    heading(
        "Research Workspace",
        "Enter a topic. GapMind will discover relevant sources automatically."
    )

    topic = st.text_input(
        "What do you want to research?",
        value=st.session_state.topic,
        placeholder=(
            "Example: Accessibility of digital healthcare "
            "services in rural India"
        )
    )

    st.caption(
        "GapMind will search the web for relevant research papers, "
        "reports and webpages."
    )

    with st.expander("Add your own sources (optional)"):

        url_text = st.text_area(
            "Additional webpage URLs",
            placeholder="Paste one URL per line",
            height=90
        )

        uploaded_files = st.file_uploader(
            "Upload additional PDF documents",
            type=["pdf"],
            accept_multiple_files=True
        )

        pasted_text = st.text_area(
            "Additional research material",
            placeholder="Paste your own research material here...",
            height=100
        )

    if st.button(
        "DISCOVER SOURCES & ANALYZE →",
        width="stretch"
    ):

        urls = [
            line.strip()
            for line in url_text.splitlines()
            if line.strip()
        ]

        run_research(
            topic,
            urls=urls,
            uploaded_files=uploaded_files,
            pasted_text=pasted_text
        )

    if sources:

        st.markdown("---")
        st.markdown("### Sources discovered and analysed")

        for index, source in enumerate(sources, 1):

            with st.expander(
                f"{index}. {source.get('title', 'Untitled source')}"
            ):

                st.write(
                    f"Type: {source.get('source_type', 'Unknown')}"
                )

                st.write(
                    "Publication date: "
                    f"{source.get('published_date') or 'Unknown'}"
                )

                if source.get("url"):
                    st.markdown(
                        f"[Open original source]({source['url']})"
                    )

                if source.get("search_snippet"):
                    st.caption(source["search_snippet"])

    if limited_sources:

        st.markdown("---")
        st.markdown("### Limited Search Evidence")

        st.warning(
            "These are search-result previews. Their full webpages "
            "could not be extracted. They are not analysed documents "
            "and are not used to generate claims or contradictions."
        )

        for index, source in enumerate(limited_sources, 1):

            with st.expander(
                f"{index}. {source.get('title', 'Untitled result')}"
            ):

                st.caption("LIMITED SEARCH PREVIEW — NOT FULL-TEXT EVIDENCE")

                st.write(
                    source.get(
                        "search_snippet",
                        "No search preview was available."
                    )
                )

                if source.get("url"):
                    st.markdown(
                        f"[Open original source]({source['url']})"
                    )

                st.caption(
                    "Extraction status: Full webpage unavailable."
                )

                st.caption(
                    f"Reason: {source.get('extraction_error', 'Not available')}"
                )


# --------------------------------------------------
# EVIDENCE INTELLIGENCE
# --------------------------------------------------

elif page == "Evidence Intelligence":

    render_brand()

    heading(
        "Evidence Intelligence",
        "Explore claims and trace them back to their original sources."
    )


    # EVIDENCE COVERAGE INTELLIGENCE
    from modules.coverage import calculate_evidence_coverage

    coverage_claims = [
        {
            "source_ids": [
                ref.get("source_id")
                for ref in item.get("references", [])
                if ref.get("source_id") is not None
            ]
        }
        for item in evidence_map
    ]

    coverage_source_ids = {
        source_id
        for claim in coverage_claims
        for source_id in claim["source_ids"]
    }

    coverage = calculate_evidence_coverage(
        coverage_claims,
        list(coverage_source_ids)
    )

    st.markdown("### Evidence Coverage Intelligence")
    st.caption(
        "Measure how widely extracted claims are linked across your sources. "
        "Multiple links do not automatically mean independent confirmation."
    )

    coverage_cols = st.columns(4)

    coverage_metrics = [
        ("MULTI-SOURCE CLAIMS",
         f"{coverage['multi_source_claims']}",
         f"{coverage['multi_source_percentage']}% of claims"),
        ("SINGLE-SOURCE CLAIMS",
         f"{coverage['single_source_claims']}",
         "Need additional source support"),
        ("UNSUPPORTED CLAIMS",
         f"{coverage['unsupported_claims']}",
         "No linked source references"),
        ("SOURCES CONTRIBUTING",
         f"{len(coverage_source_ids)}",
         f"Across {coverage['total_claims']} claims")
    ]

    for column, metric in zip(coverage_cols, coverage_metrics):
        with column:
            st.metric(metric[0], metric[1], metric[2])

    st.info(coverage["warning"])

    if not analysis:

        empty_state(
            "No research data yet",
            "Run an analysis in the Research Workspace first."
        )

    else:

        columns = st.columns(3)

        metrics = [
            ("SOURCES", len(sources), "Documents analysed", "▤"),
            ("CLAIMS", len(evidence_map), "Extracted claims", "◎"),
            (
                "POTENTIAL CONFLICTS",
                len(analysis.get("contradictions", [])),
                "Require human verification",
                "⚠"
            )
        ]

        for col, item in zip(columns, metrics):
            with col:
                metric_card(*item)

        st.markdown("### Research Summary")

        render_research_summary(
            analysis.get("summary", "No summary available."),
            sources
        )

        st.markdown("### Claim-Level Evidence Network")

        render_evidence_network(
            build_source_network(evidence_map)
        )

        st.markdown("### Extracted Claims")

        for index, item in enumerate(evidence_map, 1):

            with st.expander(
                f"Claim {index}: {item['claim'][:100]}"
            ):

                st.write(item["claim"])
                st.caption(
                    f"Confidence: {item['confidence']}"
                )

                for reference in item["references"]:

                    st.write(
                        f"Source {reference['source_id']}: "
                        f"{reference['title']}"
                    )

                    if reference.get("url"):
                        st.markdown(
                            f"[Open original source]({reference['url']})"
                        )

        st.markdown("### Potential Contradictions")

        contradictions = analysis.get("contradictions", [])

        if contradictions:

            for item in contradictions:

                with st.expander(
                    item.get("description", "Potential conflict")
                ):

                    st.write(
                        "Claim A:",
                        item.get("claim_a", "")
                    )

                    st.write(
                        "Claim B:",
                        item.get("claim_b", "")
                    )

                    st.write(
                        "Source A:",
                        item.get("claim_a_source_ids", [])
                    )

                    st.write(
                        "Source B:",
                        item.get("claim_b_source_ids", [])
                    )

                    st.warning(
                        "Human verification required."
                    )

        else:
            st.info("No potential contradictions detected.")

        st.markdown("### Freshness Warnings")

        warnings = analysis.get("freshness_warnings", [])

        if warnings:
            for warning in warnings:
                st.warning(
                    f"Source {warning.get('source_id')}: "
                    f"{warning.get('reason')}"
                )
        else:
            st.success("No freshness warnings were returned.")


# --------------------------------------------------
# INFORMATION GAPS
# --------------------------------------------------

elif page == "Information Gaps":

    render_brand()

    heading(
        "Information Gaps",
        "Identify missing answers and prioritise research blind spots."
    )

    if not analysis:

        empty_state(
            "Waiting for research",
            "Analyse sources to discover information gaps."
        )

    else:

        counts = get_priority_counts(gaps)

        columns = st.columns(3)

        metrics = [
            ("TOTAL GAPS", len(gaps), "Potential unanswered questions", "⚠"),
            ("HIGH PRIORITY", counts["high"], "Needs attention", "↑"),
            (
                "MEDIUM / LOW",
                counts["medium"] + counts["low"],
                "Additional research areas",
                "◈"
            )
        ]

        for col, item in zip(columns, metrics):
            with col:
                metric_card(*item)

        st.markdown("### Gap Impact Ranking")

        if gaps:
            render_gap_chart(gaps)

        for index, gap in enumerate(gaps, 1):

            with st.expander(
                f"Gap {index}: {gap.get('question', 'Unspecified question')}"
            ):

                st.markdown("**Why it matters**")
                st.write(gap.get("reason", "Not specified."))

                st.markdown("**Missing information**")
                st.write(
                    gap.get("missing_information", "Not specified.")
                )

                st.write(
                    f"Related sources: "
                    f"{gap.get('related_source_ids', [])}"
                )

                st.write(
                    f"Impact score: {gap.get('score', 0)}/100"
                )

                st.caption(
                    "Priority: "
                    f"{gap.get('priority', 'medium').upper()}"
                )

        st.markdown("### Analysis Limitations")

        for limitation in analysis.get("limitations", []):
            st.info(limitation)


# --------------------------------------------------
# VERIFICATION CENTER
# --------------------------------------------------

elif page == "Verification Center":

    render_brand()

    heading(
        "Verification Center",
        "Turn unanswered questions into a structured research plan."
    )

    if not analysis:

        empty_state(
            "No verification plan",
            "Run a research analysis to generate your checklist."
        )

    else:

        summary = checklist_summary(checklist)

        columns = st.columns(3)

        metrics = [
            ("TOTAL TASKS", summary["total"], "Verification questions", "▤"),
            ("VERIFIED", summary["verified"], "Completed tasks", "✓"),
            (
                "PROGRESS",
                f"{summary['completion_percent']}%",
                "Checklist completion",
                "↑"
            )
        ]

        for col, item in zip(columns, metrics):
            with col:
                metric_card(*item)

        st.progress(summary["completion_percent"] / 100)

        st.markdown("### Verification Roadmap")

        for index, item in enumerate(checklist):

            with st.container(border=True):

                st.markdown(
                    f"**{index + 1:02d}. {item['question']}**"
                )

                st.caption(item["reason"])

                statuses = [
                    "Pending verification",
                    "In progress",
                    "Verified",
                    "Unable to verify"
                ]

                current = item["status"]

                new_status = st.selectbox(
                    "Verification status",
                    statuses,
                    index=(
                        statuses.index(current)
                        if current in statuses else 0
                    ),
                    key=f"verification_{index}"
                )

                if new_status != current:
                    update_checklist_status(
                        checklist,
                        index,
                        new_status
                    )
                    st.rerun()


# --------------------------------------------------
# RESEARCH HISTORY
# --------------------------------------------------

elif page == "Research History":

    render_brand()

    heading(
        "Research History",
        "Review your previous research sessions."
    )

    runs = get_recent_runs()

    if not runs:

        empty_state(
            "No saved research sessions",
            "Your completed analyses will appear here."
        )

    else:

        for run in runs:

            with st.expander(
                f"#{run['id']} — {run['topic']}"
            ):

                st.write(f"Created: {run['created_at']}")

                st.caption(
                    "Historical result reopening is not yet implemented."
                )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown("---")

html("""
<div style="text-align:center;color:#a69a9e;
            font-size:10px;padding:18px;letter-spacing:1px;">
    GAPMIND AI · CLAIM-LEVEL EVIDENCE INTELLIGENCE
    <br><br>
    AI suggestions are not verified facts. Always inspect original sources.
</div>
""")