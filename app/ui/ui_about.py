from __future__ import annotations

import streamlit as st


def render_about_section() -> None:
    # ===== ESTILOS =====
    st.markdown(
        """
        <style>
        .about-hero {
            padding: 0.2rem 0 0.8rem 0;
        }

        .about-title {
            font-size: 2rem;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 0.4rem;
        }

        .about-subtitle {
            font-size: 0.98rem;
            line-height: 1.55;
            color: rgba(255,255,255,0.78);
            max-width: 900px;
        }

        .about-section-title {
            font-size: 1.05rem;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 0.6rem;
        }

        .about-text {
            font-size: 0.95rem;
            line-height: 1.65;
            color: #dbe4ee;
        }

        .about-muted {
            font-size: 0.9rem;
            color: rgba(255,255,255,0.65);
        }

        .about-key-list {
            padding-left: 1.1rem;
            font-size: 0.95rem;
            color: #dbe4ee;
            line-height: 1.7;
        }

        .about-highlight {
            border-radius: 14px;
            padding: 14px 16px;
            margin-top: 0.8rem;
            border: 1px solid rgba(148, 163, 184, 0.18);
            background: linear-gradient(
                90deg,
                rgba(30, 41, 59, 0.92) 0%,
                rgba(15, 23, 42, 0.88) 100%
            );
        }

        .about-highlight-title {
            font-size: 0.9rem;
            font-weight: 700;
            color: #93c5fd;
            margin-bottom: 0.25rem;
        }

        .about-highlight-text {
            font-size: 0.92rem;
            color: #dbe4ee;
        }

        .about-link a {
            color: #93c5fd !important;
            font-weight: 700;
            text-decoration: none;
        }

        .about-link a:hover {
            text-decoration: underline;
        }

        .about-footer {
            margin-top: 1.2rem;
            padding-top: 0.8rem;
            border-top: 1px solid rgba(148, 163, 184, 0.16);
            font-size: 0.85rem;
            color: rgba(255,255,255,0.55);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ===== HEADER =====
    st.markdown(
        """
        <div class="about-hero">
            <div class="about-title">Acerca del proyecto</div>
            <div class="about-subtitle">
                Sistema de soporte a la decisión (DSS) orientado a la priorización del riesgo vial
                en República Dominicana, integrando modelos predictivos, reglas de negocio y
                visualización geoespacial para apoyar la toma de decisiones.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ===== COLUMNAS =====
    col1, col2 = st.columns([1.05, 1.15])

    # ===== IZQUIERDA =====
    with col1:
        st.markdown(
            "<div class='about-section-title'>Información académica</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
**Asignatura**
INF-5120 – Sistemas de Soporte a la Decisión

**Autor**
Edwin José Nolasco

**Programa**
Doctorado en Inteligencia Artificial y Machine Learning

**Institución**
Universidad Autónoma de Santo Domingo (UASD)

**Catedrático**
Dr. Manuel Quesada Martínez
"""
        )

        st.markdown(
            "<div class='about-section-title' style='margin-top:1rem;'>Descripción del sistema</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
<div class="about-text">
Este sistema implementa un DSS híbrido que separa claramente la fase predictiva de la
fase de decisión. Primero estima el comportamiento esperado mediante modelos, y luego
transforma esa salida en categorías operativas mediante reglas interpretables.
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="about-highlight">
                <div class="about-highlight-title">Propósito</div>
                <div class="about-highlight-text">
                    Transformar resultados analíticos en decisiones interpretables,
                    priorizadas y visualmente comprensibles para análisis territorial.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ===== DERECHA =====
    with col2:
        st.markdown(
            "<div class='about-section-title'>Información técnica</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
<ul class="about-key-list">
<li><strong>Tipo:</strong> DSS híbrido</li>
<li><strong>Dominio:</strong> Seguridad vial</li>
<li><strong>Periodo:</strong> 2017–2026</li>
<li><strong>Lenguaje:</strong> Python</li>
<li><strong>Framework:</strong> Streamlit</li>
<li><strong>Librerías:</strong> Pandas, Scikit-learn, Plotly</li>
</ul>
""",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div class='about-section-title'>Arquitectura</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
<div class="about-text">
El sistema integra ingestión de datos, modelado predictivo, motor de reglas DSS
y visualización interactiva para análisis y priorización.
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div class='about-section-title'>Metodología</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
<ul class="about-key-list">
<li>Métricas Top-K (HitRate, Precision)</li>
<li>Separación predicción / decisión</li>
<li>Reglas interpretables</li>
<li>Enfoque en lectura ejecutiva</li>
</ul>
""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ===== REPOSITORIO =====
    col_repo, col_license = st.columns([1.2, 1])

    with col_repo:
        st.markdown(
            """
<div class="about-section-title">Repositorio</div>
<div class="about-link">
<a href="https://github.com/edjnolasco/dss_hotspots_rd" target="_blank">
github.com/edjnolasco/dss_hotspots_rd
</a>
</div>
<div class="about-muted">
Código fuente completo del sistema DSS, incluyendo pipeline, visualización y reglas.
</div>
""",
            unsafe_allow_html=True,
        )

    with col_license:
        st.markdown(
            """
<div class="about-section-title">Licencia</div>
<div class="about-text">
MIT License
</div>
<div class="about-muted">
Permite uso, modificación y distribución con atribución.
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ===== CIERRE =====
    st.markdown(
        """
<div class="about-section-title">Alcance del sistema</div>
<div class="about-text">
El DSS integra ranking, mapa, análisis por provincia y explicabilidad para
transformar datos en decisiones interpretables. No se limita a predecir,
sino a priorizar y justificar.
</div>

<div class="about-footer">
Proyecto académico desarrollado bajo enfoque de ingeniería DSS y analítica aplicada.
</div>
""",
        unsafe_allow_html=True,
    )