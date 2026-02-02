import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from calculo import calcular_cenario

st.set_page_config(page_title="AgroSim – Payback Agrícola", layout="wide")

st.title("AgroSim – Simulador de Plantio e Payback (igual ao Excel)")
st.caption("Lógica validada do seu Excel, incluindo custos de implantação (Ano-01..Ano-03) no payback.")

def brl(x: float) -> str:
    try:
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(x)

def to_df_series(out: dict) -> pd.DataFrame:
    s = out["series"]
    anos = [f"Ano-{a:02d}" for a in range(4, 21)]
    return pd.DataFrame({
        "ano": anos,
        "preco_por_caixa": s["preco_por_caixa"],
        "producao_total_caixas": s["producao_total_caixas"],
        "receita_total": s["receita_total"],
        "custo_total": s["custo_total"],
        "fluxo_caixa": s["fluxo_caixa"],
        "fluxo_caixa_acumulado": s["fluxo_caixa_acumulado"],
    })

def to_df_full(out: dict) -> pd.DataFrame:
    f = out["series_full"]
    return pd.DataFrame({
        "ano": f["anos_rotulo_full"],
        "receita_total": f["receita_total_full"],
        "custo_total": f["custo_total_full"],
        "fluxo_caixa": f["fluxo_caixa_full"],
        "fluxo_caixa_acumulado": f["fluxo_caixa_acumulado_full"],
    })

st.sidebar.header("1) Carregar cenário")
uploaded = st.sidebar.file_uploader("Upload de cenário (.json)", type=["json"])

try:
    default_text = open("scenario_exemplo.json", "r", encoding="utf-8").read()
except Exception:
    default_text = "{}"

scenario_text = uploaded.read().decode("utf-8") if uploaded else st.sidebar.text_area(
    "Cole aqui o JSON do cenário",
    value=default_text,
    height=320,
)

st.sidebar.header("2) Calcular")
btn = st.sidebar.button("Calcular agora")

if btn:
    try:
        scenario = json.loads(scenario_text)
        out = calcular_cenario(scenario)

        resumo = out["resumo"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Área total (ha)", f"{resumo['area_total_ha']:.2f}")

        pb_full = resumo.get("payback_ano_full")
        c2.metric("Payback (Excel)", f"Ano-{pb_full:02d}" if pb_full else "Não atingiu")

        pb = resumo.get("payback_ano")
        c3.metric("Payback (Ano-04..20)", f"Ano-{pb:02d}" if pb else "Não atingiu")

        c4.metric("FC acumulado final (Ano-20)", brl(out["series_full"]["fluxo_caixa_acumulado_full"][-1]))

        st.divider()

        df = to_df_series(out)
        df_full = to_df_full(out)

        tab1, tab2, tab3, tab4 = st.tabs(["Resumo Executivo", "Produção & Preços", "Receita & Custos", "Detalhes"])

        with tab1:
            st.subheader("Fluxo de caixa acumulado (Ano-01..Ano-20)")
            fig = plt.figure()
            plt.plot(df_full["ano"], df_full["fluxo_caixa_acumulado"])
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            st.pyplot(fig)

            st.write("Tabela (Ano-01..Ano-20)")
            st.dataframe(df_full, use_container_width=True)

        with tab2:
            st.subheader("Produção total (caixas) — Ano-04..Ano-20")
            fig = plt.figure()
            plt.plot(df["ano"], df["producao_total_caixas"])
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            st.pyplot(fig)

            st.subheader("Preço por caixa — Ano-04..Ano-20")
            fig = plt.figure()
            plt.plot(df["ano"], df["preco_por_caixa"])
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            st.pyplot(fig)

            st.dataframe(df, use_container_width=True)

        with tab3:
            st.subheader("Receita x Custo — Ano-04..Ano-20")
            fig = plt.figure()
            plt.plot(df["ano"], df["receita_total"])
            plt.plot(df["ano"], df["custo_total"])
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            st.pyplot(fig)

            st.subheader("Fluxo anual e acumulado — Ano-04..Ano-20")
            cA, cB = st.columns(2)
            with cA:
                fig = plt.figure()
                plt.plot(df["ano"], df["fluxo_caixa"])
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout()
                st.pyplot(fig)
            with cB:
                fig = plt.figure()
                plt.plot(df["ano"], df["fluxo_caixa_acumulado"])
                plt.xticks(rotation=45, ha="right")
                plt.tight_layout()
                st.pyplot(fig)

        with tab4:
            st.subheader("Talhões (resumo)")
            por_talhao = out["detalhes"]["por_talhao"]
            rows = [{
                "talhao": t["talhao"],
                "area_ha": t["area_ha"],
                "stand_pl_ha": t["stand_pl_ha"],
                "plantas_totais": t["plantas_totais"],
            } for t in por_talhao]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

            st.subheader("Custos de implantação (total R$)")
            impl = out["detalhes"]["custos"]["implantacao_total"]
            st.dataframe(pd.DataFrame({"Ano": ["Ano-01","Ano-02","Ano-03"], "Implantação (R$)": impl}), use_container_width=True)

            st.subheader("OPEX por categoria (R$/ha) — Ano-04..Ano-20")
            opex = out["detalhes"]["custos"]["opex_por_categoria_por_ha"]
            df_opex = pd.DataFrame(opex)
            df_opex.insert(0, "ano", [f"Ano-{a:02d}" for a in range(4, 21)])
            st.dataframe(df_opex, use_container_width=True)

        st.sidebar.success("Cálculo concluído ✅")

    except json.JSONDecodeError:
        st.sidebar.error("JSON inválido. Verifique se você colou o cenário completo.")
    except Exception as e:
        st.sidebar.error(f"Erro no cálculo: {e}")
else:
    st.info("Carregue/cole um cenário no menu lateral e clique em **Calcular agora**.")
