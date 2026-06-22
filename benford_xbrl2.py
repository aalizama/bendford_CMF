"""
Análisis Ley de Benford — Archivos XBRL (CMF Chile)
Instalación: pip install streamlit plotly lxml
Uso:         streamlit run benford_xbrl.py
"""

import math
import os
import tempfile
import xml.etree.ElementTree as ET

import streamlit as st
from lxml import etree

# ─── CONFIG ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ley de Benford – XBRL",
    page_icon="🔍",
    layout="wide",
)

# ─── STYLES ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"]              { font-family: 'Inter', sans-serif; }
    .stApp                                  { background-color: #0d1520; }
    [data-testid="stAppViewContainer"]      { background-color: #0d1520; }
    [data-testid="stHeader"]                { background-color: #0d1520; border-bottom: 1px solid #1e2e42; }
    [data-testid="stToolbar"]               { background-color: #0d1520; }
    [data-testid="stSidebar"]               { background-color: #0F172A; }
    [data-testid="stBottomBlockContainer"]  { background-color: #0d1520; }
    section[data-testid="stSidebar"] > div  { background-color: #112240; }

    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; max-width: 1400px; }

    .metric-card {
        background: linear-gradient(135deg, #1e2a3a 0%, #243447 100%);
        border: 1px solid #2d4060;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 12px;
    }
    .metric-label { color: #d7e3f4; font-size: 0.75rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .metric-value { color: #ffffff; font-size: 1.55rem; font-weight: 700; line-height: 1.1; }

    .section-title { color: #ffffff; font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; padding-bottom: 6px; border-bottom: 2px solid #2d4060; }

    .header-band {
        background: linear-gradient(90deg, #0f1e30, #1a3050);
        border-radius: 14px;
        padding: 22px 30px;
        margin-bottom: 24px;
        border: 1px solid #2a4060;
    }
    .header-band h1 { color: #ffffff; font-size: 1.7rem; font-weight: 700; margin: 0; }
    .header-band p  { color: #d1d5db; font-size: 0.85rem; margin: 4px 0 0 0; }

    .info-box {
        background: #111e2e;
        border: 1px solid #2d4060;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 18px;
        color: #e5e7eb;
        font-size: 0.82rem;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# ─── CONSTANTES ───────────────────────────────────────────────────────────────
BENFORD_EXPECTED = {d: math.log10(1 + 1 / d) * 100 for d in range(1, 10)}
DIGITS = list(range(1, 10))

CHART_BG = "rgba(0,0,0,0)"
GRID_CLR = "rgba(45,64,96,0.5)"
TEXT_CLR = "#FFFFFF"


# ─── FUNCIONES ────────────────────────────────────────────────────────────────
def apply_theme(fig, title=""):
    import plotly.graph_objects as go
    fig.update_layout(
        title=dict(text=title, font=dict(color="#c9d8ee", size=14), x=0.02),
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(color=TEXT_CLR, family="Inter"),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    fig.update_xaxes(gridcolor=GRID_CLR, linecolor=GRID_CLR, tickfont=dict(color=TEXT_CLR))
    fig.update_yaxes(gridcolor=GRID_CLR, linecolor=GRID_CLR, tickfont=dict(color=TEXT_CLR))
    return fig


def first_digit(n: float):
    s = f"{abs(n):.10f}".replace(".", "").lstrip("0")
    return int(s[0]) if s else None


def extract_all_values(path: str) -> list[float]:
    """Extrae todos los valores numéricos del XBRL sin filtrar por contexto."""
    with open(path, encoding="iso-8859-1") as f:
        content = f.read().encode("utf-8")
    parser = etree.XMLParser(recover=True)
    tree = etree.fromstring(content, parser)
    values = []
    for elem in tree.iter():
        val = elem.text
        if val and elem.get("contextRef"):
            val = val.strip()
            try:
                n = abs(float(val))
                if n >= 1:
                    values.append(n)
            except ValueError:
                pass
    return values


def benford_analysis(values: list[float]) -> tuple[dict, int]:
    digits = [first_digit(v) for v in values]
    digits = [d for d in digits if d is not None]
    total = len(digits)
    counts = {d: digits.count(d) for d in DIGITS}
    freq = {d: counts[d] / total * 100 if total else 0 for d in DIGITS}
    return freq, total, counts


def chi2_pvalue(chi2_stat: float, k: int = 8) -> float:
    """P-valor chi² sin scipy."""
    if chi2_stat <= 0:
        return 1.0
    a, y = k / 2.0, chi2_stat / 2.0
    try:
        from math import lgamma, log, exp
        log_factor = a * log(y) - y - lgamma(a + 1)
        s, term = 1.0, 1.0
        for n in range(1, 500):
            term *= y / (a + n)
            s += term
            if abs(term) < 1e-14 * abs(s):
                break
        p = min(max(exp(log_factor) * s, 0.0), 1.0)
        return round(1.0 - p, 4)
    except Exception:
        return float("nan")


# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-band">
  <h1>🔍 Análisis — Ley de Benford sobre Reportes XBRL</h1>
  <p>Auditoría forense de datos financieros · CMF Chile · IFRS</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="info-box">
  <b style="color:#c9d8ee;">¿Qué es la Ley de Benford?</b><br>
  En conjuntos de datos financieros reales, el primer dígito de cada cifra sigue una distribución
  logarítmica predecible: el dígito <b style="color:#60a5fa;">1</b> aparece ~30% de las veces,
  el <b style="color:#60a5fa;">2</b> ~17.6%, y así disminuye hasta el
  <b style="color:#60a5fa;">9</b> con ~4.6%. Desviaciones significativas pueden indicar
  <b style="color:#f87171;">errores, manipulación o datos sintéticos</b> y es ampliamente usada
  en auditoría forense.<br><br>
  <b style="color:#c9d8ee;">Umbrales MAD (Nigrini 2012):</b>
  &nbsp;🟢 Excelente &lt;0.6 &nbsp;|&nbsp; 🟡 Aceptable &lt;1.2 &nbsp;|&nbsp;
  🟠 Marginal &lt;1.5 &nbsp;|&nbsp; 🔴 No conforme ≥1.5
</div>
""", unsafe_allow_html=True)

# ─── CARGA DE ARCHIVOS ────────────────────────────────────────────────────────
st.sidebar.header("📁 Archivos XBRL")
uploaded_files = st.sidebar.file_uploader(
    "Sube uno o más archivos .xbrl",
    type=["xbrl", "xml"],
    accept_multiple_files=True,
)

st.sidebar.header("⚙️ Filtros")
min_val = st.sidebar.number_input(
    "Valor absoluto mínimo",
    min_value=0, value=0, step=1000,
    help="Excluye cifras menores a este valor (reduce ruido de montos pequeños)",
)
excluir_ctx = st.sidebar.multiselect(
    "Excluir contextos",
    ["CierreAnualAnterior", "CierreAnualPrevioAnterior", "TrimestreAcumuladoAnterior"],
    default=["CierreAnualAnterior", "CierreAnualPrevioAnterior"],
    help="Evita contar el mismo valor dos veces por períodos comparativos",
)
umbral_alerta = st.sidebar.slider(
    "Umbral de alerta (pp)",
    min_value=1.0, max_value=5.0, value=2.0, step=0.5,
    help="Diferencia mínima en puntos porcentuales para marcar como atípico",
)

if not uploaded_files:
    st.info("👈 Sube archivos XBRL en el panel lateral para iniciar el análisis.")
    st.stop()

# ─── PARSEO ───────────────────────────────────────────────────────────────────
@st.cache_data
def load_file(file_bytes: bytes, filename: str, min_v: float, excluir: tuple) -> tuple:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xbrl") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        with open(tmp_path, encoding="iso-8859-1") as f:
            content = f.read().encode("utf-8")
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(content, parser)
        values = []
        for elem in tree.iter():
            val = elem.text
            ctx = elem.get("contextRef", "")
            if not val or not ctx:
                continue
            if any(e in ctx for e in excluir):
                continue
            val = val.strip()
            try:
                n = abs(float(val))
                if n >= max(1, min_v):
                    values.append(n)
            except ValueError:
                pass
    finally:
        os.unlink(tmp_path)
    return values


# Parsear todos los archivos
files_data = {}
progress = st.progress(0, text="Procesando archivos...")
for i, f in enumerate(uploaded_files):
    label = f.name.replace(".xbrl", "").replace(".xml", "")
    values = load_file(f.read(), f.name, min_val, tuple(excluir_ctx))
    files_data[label] = values
    progress.progress((i + 1) / len(uploaded_files), text=f"Procesado: {f.name}")
progress.empty()

labels = list(files_data.keys())

# ─── SELECTOR DE PERÍODO ──────────────────────────────────────────────────────
import plotly.graph_objects as go

period_sel = st.selectbox("📅 Período a analizar en detalle", labels, index=len(labels) - 1)

# ─── ANÁLISIS PRINCIPAL ───────────────────────────────────────────────────────
freq, total, counts = benford_analysis(files_data[period_sel])

observed  = [freq[d] for d in DIGITS]
expected  = [BENFORD_EXPECTED[d] for d in DIGITS]
diff      = [observed[i] - expected[i] for i in range(9)]
bar_colors = ["#f87171" if abs(d) > umbral_alerta else "#3b82f6" for d in diff]

# ── Gráfico distribución ──────────────────────────────────────────────────────
fig_main = go.Figure()
fig_main.add_trace(go.Bar(
    name="Observado",
    x=[str(d) for d in DIGITS],
    y=observed,
    marker_color=bar_colors,
    marker_line_width=0,
    opacity=0.85,
    text=[f"{v:.1f}%" for v in observed],
    textposition="outside",
    textfont=dict(color="#c9d8ee", size=10),
))
fig_main.add_trace(go.Scatter(
    name="Benford esperado",
    x=[str(d) for d in DIGITS],
    y=expected,
    mode="lines+markers",
    line=dict(color="#f59e0b", width=2.5, dash="dot"),
    marker=dict(size=7, color="#f59e0b"),
))
fig_main.update_layout(
    xaxis_title="Primer dígito",
    yaxis_title="Frecuencia (%)",
    legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
    bargap=0.25,
    yaxis=dict(range=[0, max(observed + expected) * 1.3]),
    annotations=[dict(
        text=f"n = {total:,} valores",
        xref="paper", yref="paper", x=0.99, y=0.99,
        showarrow=False, font=dict(color="#5d7a9a", size=11),
        xanchor="right",
    )],
)
apply_theme(fig_main, f"Distribución Primer Dígito — {period_sel}")

# ── Gráfico desviación ────────────────────────────────────────────────────────
fig_dev = go.Figure()
fig_dev.add_trace(go.Bar(
    name="Desviación",
    x=[str(d) for d in DIGITS],
    y=diff,
    marker_color=["#f87171" if d > 0 else "#34d399" for d in diff],
    marker_line_width=0,
    text=[f"{d:+.1f}pp" for d in diff],
    textposition="outside",
    textfont=dict(color="#c9d8ee", size=10),
))
fig_dev.add_hline(y=0, line_color="#4a6080", line_width=1)
fig_dev.add_hline(y=umbral_alerta,  line_color="#f59e0b", line_width=1, line_dash="dot",
                  annotation_text=f"+{umbral_alerta}pp", annotation_font_color="#f59e0b",
                  annotation_position="right")
fig_dev.add_hline(y=-umbral_alerta, line_color="#f59e0b", line_width=1, line_dash="dot",
                  annotation_text=f"−{umbral_alerta}pp", annotation_font_color="#f59e0b",
                  annotation_position="right")
fig_dev.update_layout(
    xaxis_title="Primer dígito",
    yaxis_title="Desviación (pp)",
    showlegend=False,
)
apply_theme(fig_dev, "Desviación respecto a Benford")

col1, col2 = st.columns([3, 2])
with col1:
    st.plotly_chart(fig_main, use_container_width=True)
with col2:
    st.plotly_chart(fig_dev, use_container_width=True)

# ─── ESTADÍSTICOS ─────────────────────────────────────────────────────────────
chi2_stat = sum(
    total * ((freq[d] / 100 - BENFORD_EXPECTED[d] / 100) ** 2) / (BENFORD_EXPECTED[d] / 100)
    for d in DIGITS
)
p_value = chi2_pvalue(chi2_stat)
mad = sum(abs(freq[d] - BENFORD_EXPECTED[d]) for d in DIGITS) / 9

if mad < 0.6:
    conf_label, conf_color = "🟢 Excelente", "#34d399"
elif mad < 1.2:
    conf_label, conf_color = "🟡 Aceptable", "#f59e0b"
elif mad < 1.5:
    conf_label, conf_color = "🟠 Marginal", "#f97316"
else:
    conf_label, conf_color = "🔴 No conforme", "#f87171"

rechaza = "⚠️ Sí (α=5%)" if p_value < 0.05 else "✅ No (α=5%)"

col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
for col, label, val, color in [
    (col_s1, "Valores analizados", f"{total:,}", "#e8f0fe"),
    (col_s2, "MAD",                f"{mad:.3f}pp", conf_color),
    (col_s3, "Chi² estadístico",   f"{chi2_stat:.2f}", "#e8f0fe"),
    (col_s4, "p-valor",            f"{p_value:.4f}", "#f87171" if p_value < 0.05 else "#34d399"),
    (col_s5, "Conformidad",        conf_label, conf_color),
]:
    col.markdown(f"""
    <div class="metric-card">
      <div class="metric-label">{label}</div>
      <div class="metric-value" style="font-size:1.15rem;color:{color}">{val}</div>
    </div>""", unsafe_allow_html=True)

st.caption(f"{'⚠️ Se rechaza H₀ de conformidad con Benford' if p_value < 0.05 else '✅ No se rechaza H₀ de conformidad con Benford'} (Chi² = {chi2_stat:.2f}, p = {p_value})")
st.caption(f"{'⚠️ Se recomienda un análisis con N > 1000' if total < 1000 else '✅ Número de datos analizados aceptable para el modelo'}")
# ─── TABLA DETALLE POR DÍGITO ─────────────────────────────────────────────────
st.markdown("---")
st.markdown('<p class="section-title">📋 Detalle por Dígito</p>', unsafe_allow_html=True)

th  = "background:#1a2d45;color:#8ba0bb;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.05em;padding:8px 14px;text-align:left;border-bottom:2px solid #2d4060;"
thr = th + "text-align:right;"
td  = "padding:7px 14px;font-size:0.82rem;border-bottom:1px solid #1e3050;color:#c9d8ee;"
tdr = td + "text-align:right;font-family:monospace;"

headers = ["Dígito", "Observado n", "Observado %", "Esperado %", "Desviación (pp)", "Estado"]
hrow = "".join([f'<th style="{thr if i > 0 else th}">{h}</th>' for i, h in enumerate(headers)])
brows = ""
for d in DIGITS:
    obs_n = counts[d]
    obs_p = freq[d]
    exp_p = BENFORD_EXPECTED[d]
    dev   = obs_p - exp_p
    if abs(dev) > umbral_alerta:
        alerta = "🔴 Atípico"
        dev_color = "#f87171"
    elif abs(dev) > umbral_alerta / 2:
        alerta = "🟡 Leve"
        dev_color = "#f59e0b"
    else:
        alerta = "🟢 Normal"
        dev_color = "#34d399"
    brows += (
        f'<tr>'
        f'<td style="{td}"><b>{d}</b></td>'
        f'<td style="{tdr}">{obs_n:,}</td>'
        f'<td style="{tdr}">{obs_p:.2f}%</td>'
        f'<td style="{tdr}">{exp_p:.2f}%</td>'
        f'<td style="{tdr}color:{dev_color};">{dev:+.2f}pp</td>'
        f'<td style="{td}">{alerta}</td>'
        f'</tr>'
    )

st.markdown(f"""
<div style="overflow-x:auto;border-radius:10px;border:1px solid #2d4060;margin-bottom:20px;">
  <table style="width:100%;border-collapse:collapse;background:#111e2e;">
    <thead><tr>{hrow}</tr></thead><tbody>{brows}</tbody>
  </table>
</div>""", unsafe_allow_html=True)

# ─── COMPARATIVO MULTI-PERÍODO ────────────────────────────────────────────────
if len(files_data) > 1:
    st.markdown("---")
    st.markdown('<p class="section-title">📊 Comparativo Multi-Período</p>', unsafe_allow_html=True)

    # Mapa de calor
    import plotly.graph_objects as go
    años = labels
    matrix = []
    stats_rows = []
    for lbl in años:
        f2, t2, c2 = benford_analysis(files_data[lbl])
        row_diff = [f2[d] - BENFORD_EXPECTED[d] for d in DIGITS]
        matrix.append(row_diff)
        chi2_s = sum(
            t2 * ((f2[d] / 100 - BENFORD_EXPECTED[d] / 100) ** 2) / (BENFORD_EXPECTED[d] / 100)
            for d in DIGITS
        )
        mad_s = sum(abs(f2[d] - BENFORD_EXPECTED[d]) for d in DIGITS) / 9
        pv = chi2_pvalue(chi2_s)
        stats_rows.append({"Período": lbl, "n": t2, "MAD": round(mad_s, 4),
                            "Chi²": round(chi2_s, 2), "p-valor": pv,
                            "Rechaza H₀": "⚠️ Sí" if pv < 0.05 else "✅ No"})

    fig_heat = go.Figure(go.Heatmap(
        z=matrix,
        x=[str(d) for d in DIGITS],
        y=años,
        colorscale="RdYlGn_r",
        zmid=0,
        zmin=-5, zmax=5,
        text=[[f"{v:+.1f}pp" for v in row] for row in matrix],
        texttemplate="%{text}",
        colorbar=dict(title="Desviación (pp)", tickfont=dict(color=TEXT_CLR),
                      titlefont=dict(color=TEXT_CLR)),
    ))
    apply_theme(fig_heat, "Mapa de Calor — Desviación por Dígito y Período")
    fig_heat.update_layout(height=max(250, len(años) * 80))
    st.plotly_chart(fig_heat, use_container_width=True)

    # Evolución MAD
    mads = [r["MAD"] for r in stats_rows]
    fig_mad = go.Figure()
    fig_mad.add_trace(go.Scatter(
        x=años, y=mads, mode="lines+markers+text",
        text=[f"{v:.4f}" for v in mads],
        textposition="top center",
        line=dict(color="#f59e0b", width=2.5),
        marker=dict(size=9, color="#f59e0b"),
        name="MAD",
    ))
    for val, color, label in [(0.6, "#34d399", "Excelente"), (1.2, "#f59e0b", "Aceptable"), (1.5, "#f97316", "Marginal")]:
        fig_mad.add_hline(y=val, line_color=color, line_dash="dot", line_width=1.2,
                          annotation_text=label, annotation_font_color=color,
                          annotation_position="right")
    apply_theme(fig_mad, "Evolución del MAD por Período")
    fig_mad.update_layout(yaxis_title="MAD (pp)", xaxis_title="Período")
    st.plotly_chart(fig_mad, use_container_width=True)

    # Tabla resumen
    st.markdown('<p class="section-title">📋 Resumen Estadístico por Período</p>', unsafe_allow_html=True)
    headers2 = ["Período", "Valores (n)", "MAD", "Chi²", "p-valor", "Rechaza H₀ (α=5%)"]
    hrow2 = "".join([f'<th style="{thr if i > 0 else th}">{h}</th>' for i, h in enumerate(headers2)])
    brows2 = ""
    for r in stats_rows:
        mad_c = "#34d399" if r["MAD"] < 0.6 else ("#f59e0b" if r["MAD"] < 1.2 else ("#f97316" if r["MAD"] < 1.5 else "#f87171"))
        pv_c  = "#f87171" if r["p-valor"] < 0.05 else "#34d399"
        brows2 += (
            f'<tr>'
            f'<td style="{td}">{r["Período"]}</td>'
            f'<td style="{tdr}">{r["n"]:,}</td>'
            f'<td style="{tdr}color:{mad_c};">{r["MAD"]:.4f}</td>'
            f'<td style="{tdr}">{r["Chi²"]:.2f}</td>'
            f'<td style="{tdr}color:{pv_c};">{r["p-valor"]:.4f}</td>'
            f'<td style="{td}">{r["Rechaza H₀"]}</td>'
            f'</tr>'
        )
    st.markdown(f"""
    <div style="overflow-x:auto;border-radius:10px;border:1px solid #2d4060;margin-bottom:20px;">
      <table style="width:100%;border-collapse:collapse;background:#111e2e;">
        <thead><tr>{hrow2}</tr></thead><tbody>{brows2}</tbody>
      </table>
    </div>""", unsafe_allow_html=True)

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown("""
<br>
<div style="text-align:center;color:#9CA3AF;font-size:0.75rem;padding-bottom:10px;">
  Datos extraídos de reportes XBRL / CMF Chile · Auditoría Forense – Ley de Benford (Nigrini, 2012)
</div>
""", unsafe_allow_html=True)
