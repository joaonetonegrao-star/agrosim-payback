from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


# Convenção de timeline:
# - Implantação: Ano-01, Ano-02, Ano-03  (3 anos)
# - Operação/Receita: Ano-04..Ano-20     (17 anos)
#
# Esta lógica foi estruturada para bater com o Excel, incluindo payback_ano_full
# (acumulado desde implantação).

@dataclass(frozen=True)
class TalhaoDomain:
    talhao: int
    area_ha: float
    rua_m: float
    plantas_m: float
    prod_cx_planta_base: List[float]  # len=10 (Ano-04..Ano-13) caixas/planta
    prod_deflatores: List[float]      # len=7  (Ano-14..Ano-20) multiplicadores


def stand_plantas_por_ha(rua_m: float, planta_m: float) -> float:
    if rua_m <= 0 or planta_m <= 0:
        raise ValueError("Espaçamentos devem ser > 0.")
    return 10000.0 / (rua_m * planta_m)


def plantas_totais(area_ha: float, rua_m: float, planta_m: float) -> float:
    return stand_plantas_por_ha(rua_m, planta_m) * area_ha


def producao_talhao_ano4a20(t: TalhaoDomain) -> List[float]:
    """Produção (caixas) Ano-04..Ano-20 (17 valores)."""
    p_tot = plantas_totais(t.area_ha, t.rua_m, t.plantas_m)

    # Ano-04..Ano-13: base direta (10)
    serie = [p_tot * v for v in t.prod_cx_planta_base]

    # Ano-14..Ano-20: encadeado por deflatores (7)
    last = serie[-1] if serie else 0.0
    for d in t.prod_deflatores:
        last = last * d
        serie.append(last)

    if len(serie) != 17:
        raise ValueError("Produção Ano-04..Ano-20 deve ter 17 valores.")
    return serie


def producao_total_por_ano(talhoes: List[TalhaoDomain]) -> Tuple[List[float], float, List[List[float]]]:
    """Retorna (producao_total_ano4a20, area_total, producao_por_talhao)."""
    area_total = sum(t.area_ha for t in talhoes)
    prod_por_talhao = [producao_talhao_ano4a20(t) for t in talhoes]

    total = [0.0] * 17
    for serie in prod_por_talhao:
        for i in range(17):
            total[i] += serie[i]
    return total, area_total, prod_por_talhao


def precos_ano4a20(preco_base: float, fatores: List[float]) -> List[float]:
    """Preço Ano-04..Ano-20 (17 valores): preco_base + 16 fatores encadeados."""
    if preco_base < 0:
        raise ValueError("Preço base não pode ser negativo.")
    if len(fatores) != 16:
        raise ValueError("São necessários 16 fatores para gerar Ano-04..Ano-20.")
    precos = [preco_base]
    for f in fatores:
        precos.append(precos[-1] * float(f))
    return precos  # len=17


def receita_total_ano4a20(producao_total: List[float], precos: List[float]) -> List[float]:
    if len(producao_total) != 17 or len(precos) != 17:
        raise ValueError("Produção e preços devem ter 17 valores (Ano-04..Ano-20).")
    return [producao_total[i] * precos[i] for i in range(17)]


def custos_implantacao_total_ano1a3(itens: List[Dict], area_total: float) -> List[float]:
    """Soma implantação por ano (total R$) para Ano-01..Ano-03 (3 valores)."""
    por_ha = [0.0, 0.0, 0.0]
    for it in itens:
        v = float(it.get("valor_unitario", 0.0))
        qtd = it.get("qtd_ano", [0.0, 0.0, 0.0])
        if len(qtd) != 3:
            raise ValueError("Cada item de implantação deve ter qtd_ano com 3 valores (Ano-01..Ano-03).")
        for i in range(3):
            por_ha[i] += float(qtd[i]) * v
    return [por_ha[i] * area_total for i in range(3)]


def opex_por_categoria_por_ha_ano4a20(base_ano4: Dict[str, float], mults: Dict[str, List[float]]) -> Dict[str, List[float]]:
    """OPEX por categoria (R$/ha): base Ano-04 + 16 mults => 17 valores (Ano-04..Ano-20)."""
    out: Dict[str, List[float]] = {}
    for cat, base in base_ano4.items():
        m = mults.get(cat, [])
        if len(m) != 16:
            raise ValueError(f"Categoria {cat}: multiplicadores devem ter 16 valores (Ano-05..Ano-20).")
        serie = [float(base)]
        for x in m:
            serie.append(serie[-1] * float(x))
        out[cat] = serie
    return out


def frete_colheita_por_ha_ano4a20(
    producao_total: List[float],
    area_total: float,
    mo_unit: List[float],
    frete_unit: List[float],
) -> List[float]:
    """Frete+colheita (R$/ha): (R$/cx) * (cx/ha)"""
    if area_total <= 0:
        raise ValueError("Área total deve ser > 0.")
    if not (len(producao_total) == len(mo_unit) == len(frete_unit) == 17):
        raise ValueError("Séries devem ter 17 valores (Ano-04..Ano-20).")

    return [
        (float(mo_unit[i]) + float(frete_unit[i])) * (producao_total[i] / area_total)
        for i in range(17)
    ]


def custos_total_ano4a20(
    area_total: float,
    opex_por_cat_ha: Dict[str, List[float]],
    frete_colheita_ha: List[float],
) -> List[float]:
    """Custo total (R$) Ano-04..Ano-20 (17 valores)."""
    total_ha = [0.0] * 17
    for cat, serie in opex_por_cat_ha.items():
        if len(serie) != 17:
            raise ValueError(f"Categoria {cat}: série deve ter 17 valores.")
        for i in range(17):
            total_ha[i] += float(serie[i])
    for i in range(17):
        total_ha[i] += float(frete_colheita_ha[i])

    return [total_ha[i] * area_total for i in range(17)]


def fluxo_caixa_e_payback(receita: List[float], custos: List[float]) -> Tuple[List[float], List[float], Optional[int]]:
    """Fluxo Ano-04..Ano-20. Retorna (fc, fc_acum, payback_idx0_based)."""
    if len(receita) != 17 or len(custos) != 17:
        raise ValueError("Receita e custos devem ter 17 valores (Ano-04..Ano-20).")

    fc = [receita[i] - custos[i] for i in range(17)]
    acum = 0.0
    fc_acum = []
    payback_idx = None
    for i, v in enumerate(fc):
        acum += v
        fc_acum.append(acum)
        if payback_idx is None and acum >= 0:
            payback_idx = i  # 0 => Ano-04
    return fc, fc_acum, payback_idx


def calcular_cenario(cenario: Dict) -> Dict:
    """Calcula outputs do simulador (compatível com o JSON extraído do Excel)."""

    # 1) Talhões
    talhoes = []
    for t in cenario["talhoes"]:
        talhoes.append(
            TalhaoDomain(
                talhao=int(t["talhao"]),
                area_ha=float(t["area_ha"]),
                rua_m=float(t["rua_m"]),
                plantas_m=float(t["plantas_m"]),
                prod_cx_planta_base=[float(x) for x in t["prod_cx_planta_base"]],
                prod_deflatores=[float(x) for x in t["prod_deflatores"]],
            )
        )

    # 2) Produção
    prod_total, area_total, prod_por_talhao = producao_total_por_ano(talhoes)

    # 3) Preços e receita
    preco_base = float(cenario["precos"]["preco_base"])
    fatores = [float(x) for x in cenario["precos"]["fatores"]]
    precos = precos_ano4a20(preco_base, fatores)
    receita = receita_total_ano4a20(prod_total, precos)

    # 4) Custos
    implantacao_itens = cenario["custos"]["implantacao_itens"]
    implantacao_total = custos_implantacao_total_ano1a3(implantacao_itens, area_total)

    opex_categorias = cenario["custos"]["opex_categorias"]
    base_ano4 = {c["nome"]: float(c["base_ano4_por_ha"]) for c in opex_categorias}
    mults = {c["nome"]: [float(x) for x in c["multiplicadores"]] for c in opex_categorias}
    opex_por_cat_ha = opex_por_categoria_por_ha_ano4a20(base_ano4, mults)

    mo_unit = [float(x) for x in cenario["custos"]["colheita_mo_unit"]]
    frete_unit = [float(x) for x in cenario["custos"]["colheita_frete_unit"]]
    frete_colheita_ha = frete_colheita_por_ha_ano4a20(prod_total, area_total, mo_unit, frete_unit)

    custos_total = custos_total_ano4a20(area_total, opex_por_cat_ha, frete_colheita_ha)

    # 5) Fluxo Ano-04..Ano-20 (compatibilidade)
    fc, fc_acum, payback_idx = fluxo_caixa_e_payback(receita, custos_total)
    payback_ano = None if payback_idx is None else (payback_idx + 4)

    # 6) Fluxo completo Ano-01..Ano-20 (Excel-like)
    receita_total_full = [0.0, 0.0, 0.0] + receita
    custo_total_full = implantacao_total + custos_total
    fluxo_caixa_full = [receita_total_full[i] - custo_total_full[i] for i in range(20)]

    fluxo_caixa_acumulado_full = []
    acum_full = 0.0
    payback_ano_full = None
    for i, v in enumerate(fluxo_caixa_full):
        acum_full += v
        fluxo_caixa_acumulado_full.append(acum_full)
        if payback_ano_full is None and acum_full >= 0:
            payback_ano_full = i + 1  # Ano-01..Ano-20

    anos_rotulo = [f"{a} anos" for a in range(4, 21)]
    anos_rotulo_full = ["Ano-01", "Ano-02", "Ano-03"] + [f"Ano-{a:02d}" for a in range(4, 21)]

    # Detalhes por talhão
    detalhes_talhoes = []
    for t, serie in zip(talhoes, prod_por_talhao):
        st = stand_plantas_por_ha(t.rua_m, t.plantas_m)
        pt = plantas_totais(t.area_ha, t.rua_m, t.plantas_m)
        detalhes_talhoes.append(
            {
                "talhao": t.talhao,
                "area_ha": t.area_ha,
                "stand_pl_ha": st,
                "plantas_totais": pt,
                "producao_caixas": serie,
            }
        )

    return {
        "resumo": {
            "area_total_ha": area_total,
            "payback_ano": payback_ano,
            "payback_ano_full": payback_ano_full,
            "fc_acumulado_final": fc_acum[-1] if fc_acum else 0.0,
        },
        "series": {
            "anos_rotulo": anos_rotulo,
            "preco_por_caixa": precos,
            "producao_total_caixas": prod_total,
            "receita_total": receita,
            "custo_total": custos_total,
            "fluxo_caixa": fc,
            "fluxo_caixa_acumulado": fc_acum,
        },
        "series_full": {
            "anos_rotulo_full": anos_rotulo_full,
            "receita_total_full": receita_total_full,
            "custo_total_full": custo_total_full,
            "fluxo_caixa_full": fluxo_caixa_full,
            "fluxo_caixa_acumulado_full": fluxo_caixa_acumulado_full,
        },
        "detalhes": {
            "por_talhao": detalhes_talhoes,
            "custos": {
                "implantacao_total": implantacao_total,
                "opex_por_categoria_por_ha": opex_por_cat_ha,
                "frete_colheita_por_ha": frete_colheita_ha,
            },
        },
    }
