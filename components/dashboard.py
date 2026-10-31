import streamlit as st


def render_header():
    st.markdown(
        """
        <div class="topbar">
            <div class="brand">
                <span class="brand-icon">G</span>
                <div>
                    <div class="brand-name">GAPMIND<span> AI</span></div>
                    <div class="brand-subtitle">INTELLIGENCE PLATFORM</div>
                </div>
            </div>
            <div class="system-status">
                <span class="status-dot"></span>
                SYSTEM READY
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_heading(title, subtitle):
    st.markdown(
        f"""
        <div class="page-heading">
            <div class="eyebrow">GAPMIND / INTELLIGENCE</div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric(label, value, detail=""):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-detail">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_title(title, subtitle=None):
    subtitle_html = f"<p>{subtitle}</p>" if subtitle else ""

    st.markdown(
        f"""
        <div class="section-heading">
            <h3>{title}</h3>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status(label, status="info"):
    allowed = {
        "info": "status-info",
        "success": "status-success",
        "warning": "status-warning",
        "danger": "status-danger",
    }

    css_class = allowed.get(status, "status-info")

    st.markdown(
        f'<span class="status-pill {css_class}">{label}</span>',
        unsafe_allow_html=True,
    )


def render_empty_state(title, message):
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-icon">⌁</div>
            <h3>{title}</h3>
            <p>{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )