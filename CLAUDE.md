# Sistema de PDI: especificação para o Claude Code

## Contexto

Sistema web usado em **um único dia de teste** em um escritório de contabilidade (departamentos Fiscal, Pessoal e Contábil) e depois deixado em stand-by. É a parte prática de uma pesquisa aplicada: compara o perfil de competências de cada colaborador com o perfil de referência do cargo e gera um PDI (Plano de Desenvolvimento Individual).

Prioridades: (1) cálculos corretos e reproduzíveis, (2) fluxo simples de ponta a ponta, (3) visual limpo. Não é preciso robustez de produção.

Fluxo da pesquisa:
1. Preparação: admin/gestores definem o perfil de referência de cada cargo.
2. Avaliação: cada colaborador se autoavalia e o gestor avalia (RH opcional).
3. Cálculo: o sistema consolida as notas, calcula as métricas e gera o PDI.
4. Apresentação: colaborador e gestor veem o PDI.
5. Validação: respondem o Form 2 no Google Forms (fora do sistema).

## Stack (não trocar sem perguntar)

- Back-end: Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, NumPy, JWT (login por e-mail e senha, hash com bcrypt).
- Banco: PostgreSQL (Neon) via `DATABASE_URL`. Sem banco vetorial e sem IA generativa.
- Front-end: React + Vite + Tailwind CSS + Recharts (gráfico radar). Sem Next.js e sem biblioteca de UI pesada.
- Sem Alembic: as tabelas são criadas por `Base.metadata.create_all` e por um script de seed.
- Variáveis de ambiente: `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`. Nunca commitar `.env` (está no `.gitignore`).

## Convenções

- Interface e textos em **pt-BR**; código, tabelas e rotas em **inglês**.
- Estrutura: `backend/app/{main.py,config.py,db.py,models.py,schemas.py,security.py,engine.py,routers/}`, `backend/tests/`, `backend/seed.py`, `frontend/src/{pages,components,api.ts}`.
- `engine.py` contém só funções puras (sem banco, sem FastAPI), para testar fácil.
- Constantes ajustáveis ficam em `config.py` (ver "Regras de cálculo").
- Arquivos pequenos e focados. Não criar READMEs, docs ou abstrações que não foram pedidas.

## Competências (20, escala 0 a 10)

Escala: 0 não demonstra · 1–2 muito baixo · 3–4 baixo · 5–6 moderado · 7–8 bom · 9–10 excelente.

| code | Nome | Descrição |
|---|---|---|
| communication | Comunicação | Transmitir informações de forma clara, objetiva e adequada ao contexto. |
| teamwork | Trabalho em equipe | Colaborar, compartilhar informações e contribuir para objetivos coletivos. |
| leadership | Liderança | Orientar pessoas, assumir responsabilidades e conduzir atividades. |
| problem_solving | Resolução de problemas | Identificar problemas, analisar situações e encontrar soluções. |
| analytical_thinking | Pensamento analítico | Analisar informações, identificar padrões e usar dados para decidir. |
| organization | Organização | Organizar tarefas, informações e atividades de maneira eficiente. |
| time_management | Gestão do tempo | Priorizar atividades e cumprir prazos. |
| proactivity | Proatividade | Tomar iniciativa e antecipar necessidades sem depender de orientação. |
| adaptability | Adaptabilidade | Lidar com mudanças, novos processos, ferramentas e situações. |
| technical_knowledge | Conhecimento técnico | Domínio dos conhecimentos técnicos necessários ao cargo. |
| learning | Aprendizagem | Capacidade e disposição para adquirir conhecimentos e habilidades. |
| decision_making | Tomada de decisão | Avaliar alternativas e decidir adequadamente. |
| responsibility | Responsabilidade | Compromisso com tarefas, resultados, normas e responsabilidades. |
| autonomy | Autonomia | Executar atividades e resolver situações sem acompanhamento constante. |
| interpersonal | Relacionamento interpessoal | Manter relações profissionais respeitosas e produtivas. |
| emotional_intelligence | Inteligência emocional | Lidar com pressão, conflitos e situações diversas de forma equilibrada. |
| results_focus | Foco em resultados | Direcionar esforços para atingir objetivos e resultados. |
| creativity | Criatividade | Propor novas ideias, alternativas e formas de solucionar problemas. |
| project_management | Gestão de projetos | Planejar, acompanhar e executar atividades de projetos. |
| customer_service | Atendimento/Relacionamento com clientes | Compreender necessidades, atender bem e manter boa relação com clientes. |

## Modelo de dados

- `users`: id, name, email (único), password_hash, role (`colaborador` | `gestor` | `admin`), cargo_id (nulo para quem não é avaliado), department, tenure_band (`<6m`, `6m-1a`, `1-2a`, `2-5a`, `>5a`), is_participant (bool: entra como avaliado), consented_at, active.
- `cargos`: id, name, department.
- `competencies`: id, code, name, description (seed com as 20 acima).
- `cargo_reference`: cargo_id, competency_id, expected_level (0 a 10), provisional (bool).
- `evaluation_links`: id, evaluator_id, evaluated_id, type (`auto` | `gestor` | `rh`), status (`pendente` | `rascunho` | `completo`), submitted_at.
- `scores`: link_id, competency_id, score (0 a 10; **0 é válido**).
- `development_inputs`: link_id (único), `data` JSON. Autoavaliação: `main_goal`, `needs` (até 5 codes), `priority_competency`, `priority_reason`, `stay_in_role` (`sim`|`nao`|`nao_sei`), `future_role`, `dev_types` (lista: `curso`, `treinamento_interno`, `mentoria`, `acompanhamento`, `atividades_praticas`, `projeto_desafio`, `certificacao`, `outro`), `timeframe` (`ate_3m`|`3_6m`|`6_12m`|`mais_12m`). Gestor/RH (sobre o avaliado): `needs`, `priority_competency`, `priority_reason`.
- `action_catalog`: id, competency_id, title, type (mesmos valores de `dev_types`), description. 2 a 3 ações por competência.
- `pdis`: id, user_id, generated_at, consolidated (JSON), cosine, jaccard, config_snapshot (JSON), reference_provisional (bool).
- `pdi_items`: id, pdi_id, competency_id, gap, rank, action_id, timeframe, divergence (diferença autoavaliação − gestor, quando existir).

## Regras de cálculo (`engine.py`, tudo em `config.py`)

Constantes: `WEIGHTS = {auto: 0.3, gestor: 0.5, rh: 0.2}`, `HAS_THRESHOLD = 6`, `REQUIRED_THRESHOLD = 6`, `MIN_GAP = 1.0`, `MAX_ITEMS = 5`. (**CONFIRMAR** pesos e limiares com o pesquisador antes do teste.)

1. **Elegibilidade:** só gera PDI se houver autoavaliação `completo` e pelo menos uma avaliação de gestor `completo`. RH é opcional.
2. **Consolidação:** (a) por tipo (`auto`, `gestor`, `rh`), média das avaliações completas daquele tipo, por competência (vários gestores = média); (b) média ponderada entre os tipos presentes, com `WEIGHTS` renormalizados só entre os presentes. Calcular com precisão total e arredondar a 2 casas só na exibição.
3. **Similaridade de cosseno:** entre o vetor consolidado (20 posições) e o vetor de referência do cargo. `cos = (u·v) / (‖u‖·‖v‖)`; se algum vetor for nulo, retornar 0. Atenção: cosseno ignora magnitude (`[3,4]` e `[6,8]` dão 1,0), por isso a análise de lacunas é a base das recomendações.
4. **Jaccard:** `A` = competências com consolidado ≥ `HAS_THRESHOLD`; `B` = competências com `expected_level` ≥ `REQUIRED_THRESHOLD`. `J = |A ∩ B| / |A ∪ B|` (união vazia retorna 1,0).
5. **Lacunas:** `gap_i = expected_i − consolidated_i` (guardar com sinal). Candidatas: `gap_i >= MIN_GAP`.
6. **Priorização (determinística):** ordenar por `gap` decrescente; desempate: competência prioritária (do colaborador ou do gestor) primeiro, depois as citadas em `needs`, depois menor nota consolidada, depois ordem alfabética do `code`. Pegar até `MAX_ITEMS`.
7. **Ação sugerida:** do `action_catalog` da competência, preferir o `type` presente em `dev_types` do colaborador; senão a primeira por id.
8. **Prazo:** para a competência prioritária do colaborador, usar o `timeframe` dele; para as demais, `gap >= 4` → `6_12m`, `gap >= 2` → `3_6m`, senão `ate_3m`.
9. **Divergência:** por competência, nota da autoavaliação menos a do gestor. Guardar e exportar (insumo qualitativo).
10. Gerar de novo substitui o PDI anterior do usuário. Se algum `cargo_reference` do cargo for `provisional`, marcar o PDI e mostrar aviso na tela e no CSV.
11. **Sem LLM:** nenhuma chamada a modelo de IA no sistema.

## Perfis de acesso

- **colaborador:** vê e responde apenas as suas avaliações (autoavaliação); vê o próprio PDI depois de gerado; não vê as notas individuais dadas pelo gestor (**CONFIRMAR**); não vê dados de outros.
- **gestor:** responde as avaliações em que é avaliador; vê o time (avaliados vinculados a ele): notas, status e PDIs. Gestores que também são avaliados (Tércio, Andreza) têm os dois papéis.
- **admin:** tudo: usuários, cargos, perfis de referência, vínculos de avaliação, catálogo de ações, status geral, gerar PDI, exportar CSV. O admin não entra na amostra.
- Primeiro login: tela de consentimento (texto do termo a definir, placeholder agora) e gravação de `consented_at`; sem aceitar, não avança.
- Toda rota valida o papel e o escopo no back-end (não confiar só no front).

## API (resumo)

- `POST /auth/login`, `GET /me`, `POST /me/consent`.
- Admin: CRUD `/users`, `/cargos`, `/cargos/{id}/reference`, `/links`, `/catalog`; `GET /admin/status`; `POST /admin/pdi/{user_id}/generate`; `GET /admin/export/csv`.
- Avaliações: `GET /evaluations/mine`; `GET /evaluations/{link_id}`; `PUT /evaluations/{link_id}` (rascunho); `POST /evaluations/{link_id}/submit` (valida as 20 notas).
- PDI e time: `GET /pdi/{user_id}` (dono, gestor do avaliado ou admin); `GET /team` (gestor).

## Telas (React, pt-BR, responsivas)

`/login` · `/consentimento` · `/minhas-avaliacoes` · `/avaliacao/:linkId` (20 competências com descrição e seletor 0 a 10, rascunho e envio, depois campos de necessidades e objetivos) · `/meu-pdi` (radar colaborador vs. cargo, cosseno e Jaccard, lista de lacunas e ações) · `/equipe` e `/equipe/:userId` (gestor) · `/admin` (usuários, cargos e perfis de referência, vínculos, catálogo, status pendente/completo, exportar CSV).

## Seed (`backend/seed.py`)

- 20 competências (tabela acima).
- Cargos: Coordenador Fiscal, Coordenador Contábil, Controller, Analista Fiscal, Analista de Departamento Pessoal, Auxiliar Contábil, Analista de RH.
- `cargo_reference` provisório: `expected_level = 7` em todas as competências, `provisional = true` (o admin ajusta na tela).
- Usuários (e-mails fictícios `nome@exemplo.com`, senha temporária gerada e impressa no console, não gravada no código):
  - admin: o pesquisador.
  - gestores (não avaliados): Antonio Bernardo, Tatiana Bernardo; Alexandre Magno (RH, sem vínculos por estar de férias).
  - avaliados (`is_participant = true`): Tércio (Coord. Fiscal, gestor), Andreza (Coord. Contábil, gestor), Israel (Controller), Daniel (Analista Fiscal), Pedro (Analista de DP; atua também no fiscal), Maria Helena (Analista de DP), Ivanilda (Analista de DP), Paulo Neto (Auxiliar Contábil), Vinícius (Auxiliar Contábil).
- Vínculos `auto` para todos os avaliados e vínculos `gestor`: Antonio → Tércio, Andreza, Israel; Tatiana → Maria Helena, Ivanilda, Pedro; Tércio → Daniel, Pedro; Andreza → Paulo Neto, Vinícius. (**CONFIRMAR** com o pesquisador; editáveis na tela de admin.)
- Catálogo: 2 a 3 ações por competência (rascunho; o pesquisador revisa).

## Exportação CSV (admin)

Três arquivos: (1) `scores`: avaliado, tipo de avaliador, competência, nota; (2) `resumo`: avaliado, cargo, cosseno, Jaccard, nº de lacunas, `reference_provisional`; (3) `pdi`: avaliado, competência, lacuna, ação, prazo, divergência. Só avaliados com status completo entram na análise.

## Testes (pytest, só `engine.py`)

Valores conferidos à mão: cosseno de vetores idênticos = 1; ortogonais = 0; `[3,4]` vs `[6,8]` = 1; Jaccard de `{a,b,c}` e `{b,c,d}` = 0,5; consolidação com pesos renormalizados quando falta o RH; nota 0 tratada como 0 (e não como "vazio"); desempate determinístico na priorização.

## Ordem de trabalho (uma sessão por item; `git commit` no fim de cada uma)

1. Modelos, `config.py`, `seed.py`. Pronto quando `seed.py` roda e popula tudo.
2. Login JWT, papéis e escopos. Pronto quando cada papel só acessa o que deve.
3. `engine.py` + testes. Pronto quando `pytest` passa.
4. Rotas e telas de avaliação (autoavaliação e gestor).
5. Geração do PDI e tela `/meu-pdi` com radar.
6. Painéis do gestor e do admin, status e exportação CSV.
7. Entrega local: back com `uvicorn app.main:app --host 0.0.0.0`, front com `vite --host`, acesso pelo IP da rede do escritório (ajustar `CORS_ORIGINS`).

## Regras para o agente (economia de tokens)

- Faça só o que a sessão pede. Não refatore código não relacionado.
- Não leia o repositório inteiro; abra só os arquivos necessários.
- Pergunte antes de adicionar dependência nova.
- Rode os testes após mexer em `engine.py`.
- Ao terminar, resuma em até 5 linhas: o que foi feito, o que falta e como testar.
- Marque qualquer decisão incerta com `# TODO(confirmar)` em vez de inventar.

## Fora de escopo (não construir)

Recuperação de senha, e-mail e notificações, acompanhamento detalhado de progresso do PDI, IA generativa, banco vetorial, multi-empresa.
