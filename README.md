# AgroSim (Streamlit) – Simulador de Plantio & Payback (igual ao Excel)

Este pacote entrega um **app com tela** (Streamlit) que reproduz a lógica de cálculo validada do Excel,
incluindo **custos de implantação (Ano-01..Ano-03)** no payback (`payback_ano_full`).

## Como rodar (Windows)
1) Instale Python 3.11+ (se possível) marcando "Add Python to PATH".
2) Abra o terminal na pasta do projeto e rode:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

O navegador abrirá o app.

## Se você não consegue instalar Python no PC
Você pode rodar este app em outro computador (TI) ou publicar em uma plataforma de Streamlit.
Quando você quiser, eu te passo o passo a passo mais simples.

## Arquivos
- app.py: interface do app
- calculo.py: motor de cálculo (igual Excel)
- scenario_exemplo.json: cenário extraído do seu Excel (para testar)
- requirements.txt: dependências
