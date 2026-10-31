import plotly.graph_objects as go
import networkx as nx
import streamlit as st


def render_evidence_network(network_data):
    nodes = network_data.get("nodes", [])
    edges = network_data.get("edges", [])

    if not nodes:
        st.info("Evidence network will appear after analysis.")
        return

    graph = nx.Graph()

    for node in nodes:
        graph.add_node(
            node["id"],
            label=node["label"],
            node_type=node["type"]
        )

    for edge in edges:
        graph.add_edge(edge["source"], edge["target"])

    positions = nx.spring_layout(
        graph,
        seed=42,
        k=1.2,
        iterations=60
    )

    edge_x = []
    edge_y = []

    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]

        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=1.5, color="#164e70"),
        hoverinfo="none"
    )

    source_x = []
    source_y = []
    source_labels = []

    claim_x = []
    claim_y = []
    claim_labels = []

    for node in nodes:
        x, y = positions[node["id"]]

        if node["type"] == "source":
            source_x.append(x)
            source_y.append(y)
            source_labels.append(node["label"])
        else:
            claim_x.append(x)
            claim_y.append(y)
            claim_labels.append(node["label"])

    source_trace = go.Scatter(
        x=source_x,
        y=source_y,
        mode="markers+text",
        text=source_labels,
        textposition="bottom center",
        textfont=dict(color="#7dd3fc", size=10),
        hovertext=source_labels,
        hoverinfo="text",
        marker=dict(
            size=18,
            color="#06b6d4",
            line=dict(width=2, color="#a5f3fc")
        ),
        name="Sources"
    )

    claim_trace = go.Scatter(
        x=claim_x,
        y=claim_y,
        mode="markers+text",
        text=claim_labels,
        textposition="top center",
        textfont=dict(color="#e2e8f0", size=9),
        hovertext=claim_labels,
        hoverinfo="text",
        marker=dict(
            size=13,
            color="#2563eb",
            line=dict(width=2, color="#93c5fd")
        ),
        name="Claims"
    )

    figure = go.Figure(
        data=[edge_trace, source_trace, claim_trace]
    )

    figure.update_layout(
        height=480,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=True,
        legend=dict(
            font=dict(color="#94a3b8"),
            bgcolor="rgba(0,0,0,0)"
        ),
        xaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False
        ),
        yaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False
        ),
        hoverlabel=dict(
            bgcolor="#0f172a",
            font_color="#e2e8f0"
        )
    )

    st.plotly_chart(
        figure,
        width="stretch",
        config={"displayModeBar": False}
    )


def render_gap_chart(gaps):
    if not gaps:
        st.info("No information gaps have been identified yet.")
        return

    labels = [
        gap.get("question", "Unspecified gap")[:55]
        for gap in gaps
    ]

    scores = [
        gap.get("score", 0)
        for gap in gaps
    ]

    figure = go.Figure(
        go.Bar(
            x=scores,
            y=labels,
            orientation="h",
            marker=dict(
                color=scores,
                colorscale=[
                    [0, "#164e70"],
                    [0.5, "#0891b2"],
                    [1, "#22d3ee"]
                ],
                showscale=False
            ),
            text=scores,
            textposition="outside"
        )
    )

    figure.update_layout(
        height=max(250, len(gaps) * 65),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1"),
        margin=dict(l=10, r=35, t=15, b=15),
        xaxis=dict(
            title="Heuristic impact score",
            range=[0, 115],
            gridcolor="#1e293b"
        ),
        yaxis=dict(
            autorange="reversed",
            gridcolor="rgba(0,0,0,0)"
        )
    )

    st.plotly_chart(
        figure,
        width="stretch",
        config={"displayModeBar": False}
    )