import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bcrypt
from sqlalchemy import func, select

from app.config import DATABASE_URL
from app.db import Base, get_engine, get_session_factory
from app.models import (  # noqa: F401
    ActionCatalog,
    Cargo,
    CargoReference,
    Competency,
    DevelopmentInput,
    EvaluationLink,
    Pdi,
    PdiItem,
    Score,
    User,
)

PASSWORD_ALPHABET = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"

COMPETENCIES = [
    ("communication", "Comunicação", "Transmitir informações de forma clara, objetiva e adequada ao contexto."),
    ("teamwork", "Trabalho em equipe", "Colaborar, compartilhar informações e contribuir para objetivos coletivos."),
    ("leadership", "Liderança", "Orientar pessoas, assumir responsabilidades e conduzir atividades."),
    ("problem_solving", "Resolução de problemas", "Identificar problemas, analisar situações e encontrar soluções."),
    ("analytical_thinking", "Pensamento analítico", "Analisar informações, identificar padrões e usar dados para decidir."),
    ("organization", "Organização", "Organizar tarefas, informações e atividades de maneira eficiente."),
    ("time_management", "Gestão do tempo", "Priorizar atividades e cumprir prazos."),
    ("proactivity", "Proatividade", "Tomar iniciativa e antecipar necessidades sem depender de orientação."),
    ("adaptability", "Adaptabilidade", "Lidar com mudanças, novos processos, ferramentas e situações."),
    ("technical_knowledge", "Conhecimento técnico", "Domínio dos conhecimentos técnicos necessários ao cargo."),
    ("learning", "Aprendizagem", "Capacidade e disposição para adquirir conhecimentos e habilidades."),
    ("decision_making", "Tomada de decisão", "Avaliar alternativas e decidir adequadamente."),
    ("responsibility", "Responsabilidade", "Compromisso com tarefas, resultados, normas e responsabilidades."),
    ("autonomy", "Autonomia", "Executar atividades e resolver situações sem acompanhamento constante."),
    ("interpersonal", "Relacionamento interpessoal", "Manter relações profissionais respeitosas e produtivas."),
    ("emotional_intelligence", "Inteligência emocional", "Lidar com pressão, conflitos e situações diversas de forma equilibrada."),
    ("results_focus", "Foco em resultados", "Direcionar esforços para atingir objetivos e resultados."),
    ("creativity", "Criatividade", "Propor novas ideias, alternativas e formas de solucionar problemas."),
    ("project_management", "Gestão de projetos", "Planejar, acompanhar e executar atividades de projetos."),
    ("customer_service", "Atendimento/Relacionamento com clientes", "Compreender necessidades, atender bem e manter boa relação com clientes."),
]

CARGOS = [
    ("Coordenador Fiscal", "Fiscal"),
    ("Coordenador Contábil", "Contábil"),
    ("Controller", "Contábil"),
    ("Analista Fiscal", "Fiscal"),
    ("Analista de Departamento Pessoal", "Pessoal"),
    ("Auxiliar Contábil", "Contábil"),
    ("Analista de RH", "Pessoal"),  # TODO(confirmar) departamento do cargo Analista de RH
]

# TODO(confirmar) nomes completos, e-mails reais, tempo de casa e departamentos dos gestores
USERS = [
    {
        "name": "Pesquisador",
        "email": "pesquisador@exemplo.com",
        "role": "admin",
        "cargo": None,
        "department": None,
        "tenure_band": None,
        "is_participant": False,
    },
    {
        "name": "Antonio Bernardo",
        "email": "antonio.bernardo@exemplo.com",
        "role": "gestor",
        "cargo": None,
        "department": "Fiscal",
        "tenure_band": ">5a",
        "is_participant": False,
    },
    {
        "name": "Tatiana Bernardo",
        "email": "tatiana.bernardo@exemplo.com",
        "role": "gestor",
        "cargo": None,
        "department": "Pessoal",
        "tenure_band": ">5a",
        "is_participant": False,
    },
    {
        "name": "Alexandre Magno",
        "email": "alexandre.magno@exemplo.com",
        "role": "gestor",
        "cargo": None,
        "department": "Pessoal",
        "tenure_band": ">5a",
        "is_participant": False,
    },
    {
        "name": "Tércio",
        "email": "tercio@exemplo.com",
        "role": "gestor",
        "cargo": "Coordenador Fiscal",
        "department": "Fiscal",
        "tenure_band": "2-5a",
        "is_participant": True,
    },
    {
        "name": "Andreza",
        "email": "andreza@exemplo.com",
        "role": "gestor",
        "cargo": "Coordenador Contábil",
        "department": "Contábil",
        "tenure_band": "2-5a",
        "is_participant": True,
    },
    {
        "name": "Israel",
        "email": "israel@exemplo.com",
        "role": "colaborador",
        "cargo": "Controller",
        "department": "Contábil",
        "tenure_band": "1-2a",
        "is_participant": True,
    },
    {
        "name": "Daniel",
        "email": "daniel@exemplo.com",
        "role": "colaborador",
        "cargo": "Analista Fiscal",
        "department": "Fiscal",
        "tenure_band": "1-2a",
        "is_participant": True,
    },
    {
        "name": "Pedro",
        "email": "pedro@exemplo.com",
        "role": "colaborador",
        "cargo": "Analista de Departamento Pessoal",
        "department": "Pessoal",
        "tenure_band": "1-2a",
        "is_participant": True,
    },
    {
        "name": "Maria Helena",
        "email": "maria.helena@exemplo.com",
        "role": "colaborador",
        "cargo": "Analista de Departamento Pessoal",
        "department": "Pessoal",
        "tenure_band": "2-5a",
        "is_participant": True,
    },
    {
        "name": "Ivanilda",
        "email": "ivanilda@exemplo.com",
        "role": "colaborador",
        "cargo": "Analista de Departamento Pessoal",
        "department": "Pessoal",
        "tenure_band": "2-5a",
        "is_participant": True,
    },
    {
        "name": "Paulo Neto",
        "email": "paulo.neto@exemplo.com",
        "role": "colaborador",
        "cargo": "Auxiliar Contábil",
        "department": "Contábil",
        "tenure_band": "6m-1a",
        "is_participant": True,
    },
    {
        "name": "Vinícius",
        "email": "vinicius@exemplo.com",
        "role": "colaborador",
        "cargo": "Auxiliar Contábil",
        "department": "Contábil",
        "tenure_band": "6m-1a",
        "is_participant": True,
    },
]

# TODO(confirmar) vínculos de gestor com o pesquisador; editáveis na tela de admin
GESTOR_LINKS = [
    ("antonio.bernardo@exemplo.com", "tercio@exemplo.com"),
    ("antonio.bernardo@exemplo.com", "andreza@exemplo.com"),
    ("antonio.bernardo@exemplo.com", "israel@exemplo.com"),
    ("tatiana.bernardo@exemplo.com", "maria.helena@exemplo.com"),
    ("tatiana.bernardo@exemplo.com", "ivanilda@exemplo.com"),
    ("tatiana.bernardo@exemplo.com", "pedro@exemplo.com"),
    ("tercio@exemplo.com", "daniel@exemplo.com"),
    ("tercio@exemplo.com", "pedro@exemplo.com"),
    ("andreza@exemplo.com", "paulo.neto@exemplo.com"),
    ("andreza@exemplo.com", "vinicius@exemplo.com"),
]

# rascunho; o pesquisador revisa
CATALOG = {
    "communication": [
        ("curso", "Curso de comunicação objetiva", "Participar de curso sobre clareza, objetividade e adequação da mensagem ao interlocutor."),
        ("atividades_praticas", "Prática de feedbacks curtos", "Ensaiar e registrar feedbacks objetivos em reuniões semanais da equipe."),
    ],
    "teamwork": [
        ("treinamento_interno", "Treinamento de colaboração", "Participar de treinamento interno sobre compartilhamento de informações e trabalho conjunto."),
        ("projeto_desafio", "Projeto compartilhado", "Assumir uma entrega conjunta com outro departamento, com alinhamento periódico."),
    ],
    "leadership": [
        ("mentoria", "Mentoria de liderança", "Acompanhar um gestor em reuniões de condução de equipe e discutir as decisões tomadas."),
        ("acompanhamento", "Condução assistida de reuniões", "Facilitar reuniões curtas com observação e retorno do gestor."),
    ],
    "problem_solving": [
        ("curso", "Curso de resolução de problemas", "Estudar um método simples de definição do problema, causas e alternativas."),
        ("atividades_praticas", "Análise de um caso real", "Documentar um problema recorrente da rotina e propor duas alternativas de solução."),
    ],
    "analytical_thinking": [
        ("treinamento_interno", "Leitura de indicadores da área", "Treinar a leitura de relatórios e indicadores usados no departamento."),
        ("atividades_praticas", "Painel simples de dados", "Montar um acompanhamento periódico com os dados mais usados no cargo."),
    ],
    "organization": [
        ("acompanhamento", "Organização da rotina com o gestor", "Revisar juntos a forma de organizar tarefas, pastas e filas de trabalho."),
        ("curso", "Curso de organização do trabalho", "Participar de curso sobre organização de tarefas e informações."),
    ],
    "time_management": [
        ("mentoria", "Priorização da semana", "Definir com o gestor as prioridades da semana e revisar o cumprimento dos prazos."),
        ("atividades_praticas", "Registro de prazos", "Manter um quadro simples de prazos das entregas principais por 30 dias."),
    ],
    "proactivity": [
        ("acompanhamento", "Antecipação de demandas", "Combinar com o gestor duas situações em que a pessoa deve agir sem esperar orientação."),
        ("projeto_desafio", "Melhoria de um processo", "Propor e testar uma melhoria pequena em um processo da rotina."),
    ],
    "adaptability": [
        ("treinamento_interno", "Novas ferramentas da área", "Participar de treinamento sobre mudanças de processo ou sistema em andamento."),
        ("atividades_praticas", "Rodízio supervisionado", "Executar, com suporte, uma atividade nova por um período definido."),
    ],
    "technical_knowledge": [
        ("curso", "Atualização técnica do cargo", "Fazer um curso técnico alinhado às normas e rotinas do cargo."),
        ("certificacao", "Certificação da área", "Iniciar preparação para certificação relevante à função."),
    ],
    "learning": [
        ("mentoria", "Plano de estudo quinzenal", "Definir com um mentor dois temas técnicos para estudar a cada quinzena."),
        ("curso", "Curso de aprendizagem contínua", "Participar de curso curto sobre como estudar e aplicar novos conteúdos no trabalho."),
    ],
    "decision_making": [
        ("acompanhamento", "Decisões comentadas", "Revisar com o gestor decisões recentes, critérios usados e alternativas descartadas."),
        ("atividades_praticas", "Matriz simples de decisão", "Usar uma matriz de prós e contras em três decisões da rotina."),
    ],
    "responsibility": [
        ("acompanhamento", "Acordo de entregas", "Combinar com o gestor responsáveis, prazos e critérios de conclusão das tarefas."),
        ("treinamento_interno", "Normas e rotinas do escritório", "Revisar normas internas, prazos legais e responsabilidades do cargo."),
    ],
    "autonomy": [
        ("mentoria", "Checklist de autonomia", "Definir com o mentor o que pode ser feito sozinho e quando acionar o gestor."),
        ("projeto_desafio", "Entrega ponta a ponta", "Conduzir uma demanda completa, com pontos de checagem combinados."),
    ],
    "interpersonal": [
        ("treinamento_interno", "Relações profissionais no escritório", "Participar de treinamento sobre comunicação respeitosa e trabalho entre áreas."),
        ("atividades_praticas", "Alinhamento entre departamentos", "Conduzir um alinhamento curto com outra área sobre uma demanda compartilhada."),
    ],
    "emotional_intelligence": [
        ("curso", "Curso de inteligência emocional", "Participar de curso sobre pressão, conflitos e autorregulação no trabalho."),
        ("mentoria", "Conversas de situações difíceis", "Discutir com o mentor duas situações recentes de pressão ou conflito."),
    ],
    "results_focus": [
        ("acompanhamento", "Metas da quinzena", "Definir metas observáveis da quinzena e revisar o resultado com o gestor."),
        ("projeto_desafio", "Meta de redução de retrabalho", "Escolher um indicador simples e buscar melhora em um ciclo de 30 dias."),
    ],
    "creativity": [
        ("atividades_praticas", "Caixa de ideias da rotina", "Registrar três alternativas para um processo que gera retrabalho."),
        ("treinamento_interno", "Oficina de melhoria", "Participar de oficina interna para propor melhorias em processos da área."),
    ],
    "project_management": [
        ("curso", "Curso introdutório de projetos", "Estudar planejamento, acompanhamento e encerramento de atividades de projeto."),
        ("projeto_desafio", "Mini-projeto da área", "Planejar e acompanhar um mini-projeto com início, prazos e entrega."),
    ],
    "customer_service": [
        ("treinamento_interno", "Atendimento ao cliente do escritório", "Revisar padrões de atendimento, prazos de retorno e tom da comunicação com clientes."),
        ("acompanhamento", "Atendimento observado", "Acompanhar atendimentos e receber retorno sobre clareza e relacionamento."),
    ],
}


def _password() -> str:
    return "".join(secrets.choice(PASSWORD_ALPHABET) for _ in range(12))


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _get_or_create_competencies(session) -> dict[str, Competency]:
    by_code: dict[str, Competency] = {}
    for code, name, description in COMPETENCIES:
        row = session.scalar(select(Competency).where(Competency.code == code))
        if row is None:
            row = Competency(code=code, name=name, description=description)
            session.add(row)
        else:
            row.name = name
            row.description = description
        by_code[code] = row
    session.flush()
    return by_code


def _get_or_create_cargos(session) -> dict[str, Cargo]:
    by_name: dict[str, Cargo] = {}
    for name, department in CARGOS:
        row = session.scalar(select(Cargo).where(Cargo.name == name))
        if row is None:
            row = Cargo(name=name, department=department)
            session.add(row)
        else:
            row.department = department
        by_name[name] = row
    session.flush()
    return by_name


def _ensure_references(session, cargos: dict[str, Cargo], competencies: dict[str, Competency]) -> None:
    for cargo in cargos.values():
        for competency in competencies.values():
            exists = session.scalar(
                select(CargoReference).where(
                    CargoReference.cargo_id == cargo.id,
                    CargoReference.competency_id == competency.id,
                )
            )
            if exists is None:
                session.add(
                    CargoReference(
                        cargo_id=cargo.id,
                        competency_id=competency.id,
                        expected_level=7,
                        provisional=True,
                    )
                )


def _ensure_users(session, cargos: dict[str, Cargo]) -> tuple[dict[str, User], list[tuple[str, str, str]]]:
    created: list[tuple[str, str, str]] = []
    by_email: dict[str, User] = {}
    for item in USERS:
        row = session.scalar(select(User).where(User.email == item["email"]))
        cargo = cargos.get(item["cargo"]) if item["cargo"] else None
        if row is None:
            plain = _password()
            row = User(
                name=item["name"],
                email=item["email"],
                password_hash=_hash_password(plain),
                role=item["role"],
                cargo_id=cargo.id if cargo else None,
                department=item["department"],
                tenure_band=item["tenure_band"],
                is_participant=item["is_participant"],
                active=True,
            )
            session.add(row)
            created.append((item["name"], item["email"], plain))
        else:
            row.name = item["name"]
            row.role = item["role"]
            row.cargo_id = cargo.id if cargo else None
            row.department = item["department"]
            row.tenure_band = item["tenure_band"]
            row.is_participant = item["is_participant"]
            row.active = True
        by_email[item["email"]] = row
    session.flush()
    return by_email, created


def _ensure_links(session, users: dict[str, User]) -> None:
    participants = [u for u in users.values() if u.is_participant]
    for user in participants:
        exists = session.scalar(
            select(EvaluationLink).where(
                EvaluationLink.evaluator_id == user.id,
                EvaluationLink.evaluated_id == user.id,
                EvaluationLink.type == "auto",
            )
        )
        if exists is None:
            session.add(
                EvaluationLink(
                    evaluator_id=user.id,
                    evaluated_id=user.id,
                    type="auto",
                    status="pendente",
                )
            )

    for evaluator_email, evaluated_email in GESTOR_LINKS:
        evaluator = users[evaluator_email]
        evaluated = users[evaluated_email]
        exists = session.scalar(
            select(EvaluationLink).where(
                EvaluationLink.evaluator_id == evaluator.id,
                EvaluationLink.evaluated_id == evaluated.id,
                EvaluationLink.type == "gestor",
            )
        )
        if exists is None:
            session.add(
                EvaluationLink(
                    evaluator_id=evaluator.id,
                    evaluated_id=evaluated.id,
                    type="gestor",
                    status="pendente",
                )
            )


def _ensure_catalog(session, competencies: dict[str, Competency]) -> None:
    for code, actions in CATALOG.items():
        competency = competencies[code]
        for action_type, title, description in actions:
            row = session.scalar(
                select(ActionCatalog).where(
                    ActionCatalog.competency_id == competency.id,
                    ActionCatalog.title == title,
                )
            )
            if row is None:
                session.add(
                    ActionCatalog(
                        competency_id=competency.id,
                        title=title,
                        type=action_type,
                        description=description,
                    )
                )
            else:
                row.type = action_type
                row.description = description


def _print_counts(session) -> None:
    tables = [
        ("competencies", Competency),
        ("cargos", Cargo),
        ("cargo_reference", CargoReference),
        ("users", User),
        ("evaluation_links", EvaluationLink),
        ("scores", Score),
        ("development_inputs", DevelopmentInput),
        ("action_catalog", ActionCatalog),
        ("pdis", Pdi),
        ("pdi_items", PdiItem),
    ]
    print("\nContagem por tabela:")
    for name, model in tables:
        count = session.scalar(select(func.count()).select_from(model))
        print(f"  {name}: {count}")


def main() -> None:
    if not DATABASE_URL:
        print("backend/.env ou DATABASE_URL está vazio. Preencha DATABASE_URL e rode o seed de novo.")
        sys.exit(1)

    engine = get_engine()
    Base.metadata.create_all(engine)
    SessionLocal = get_session_factory(engine)

    with SessionLocal() as session:
        competencies = _get_or_create_competencies(session)
        cargos = _get_or_create_cargos(session)
        _ensure_references(session, cargos, competencies)
        users, created = _ensure_users(session, cargos)
        _ensure_links(session, users)
        _ensure_catalog(session, competencies)
        session.commit()

        if created:
            print("Senhas temporárias (primeira execução / usuários novos). Guarde agora; só o hash fica no banco.")
            for name, email, plain in created:
                print(f"  {name} <{email}>: {plain}")
        else:
            print("Nenhum usuário novo. Senhas temporárias não foram geradas de novo.")

        _print_counts(session)


if __name__ == "__main__":
    main()
