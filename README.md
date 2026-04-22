# ETL Motéis — Dashboard

Dashboard operacional para visualização dos dados da rede de motéis. Construído com **Streamlit** e conectado ao **Supabase (PostgreSQL)**, consumindo os dados carregados pelo pipeline [ETL-MOTEIS](https://github.com/LealGOA/ETL-MOTEIS).

---

## Funcionalidades

- **Visão Diária** — calendário mensal com saídas, faturamento e ticket médio por dia; destaque de feriados e fins de semana
- **Visão Mensal** — comparativo por unidade: saídas, faturamento e deltas em relação ao mesmo período do mês anterior
- Filtro por unidade e navegação entre meses
- Layout mobile-first (responsivo)
- Acesso protegido por senha

---

## Arquitetura

```
Supabase (PostgreSQL)   ←   pipeline ETL-MOTEIS (GitHub Actions, diário 08:00 BRT)
        │
        ▼
  Streamlit app (app.py)
  ├── database.py   # queries ao Supabase
  ├── calendar_view.py  # renderização do calendário
  └── utils.py      # formatação de números e moeda
```

---

## Configuração

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar secrets

Copie `.streamlit/secrets.example.toml` para `.streamlit/secrets.toml` e preencha:

```toml
DATABASE_URL = "postgresql://postgres.[projeto]:[senha]@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"
DASHBOARD_PASSWORD = "sua-senha-aqui"
```

### 3. Rodar localmente

```bash
streamlit run app.py
```

---

## Deploy (Streamlit Community Cloud)

1. Conectar o repositório em [share.streamlit.io](https://share.streamlit.io)
2. Em **Settings → Secrets**, adicionar o conteúdo do `secrets.toml`
3. O app atualiza automaticamente a cada push na branch `main`

---

## Autor

Guilherme Leal — sistema de gestão operacional de rede de motéis.
