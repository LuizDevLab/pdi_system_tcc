from tests.conftest import PASSWORD


def test_login_valido(client, users):
    r = client.post("/auth/login", json={"email": "colab@exemplo.com", "password": PASSWORD})
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.json()["user"]["role"] == "colaborador"


def test_login_invalido_mensagem_generica(client, users):
    senha_errada = client.post("/auth/login", json={"email": "colab@exemplo.com", "password": "x"})
    sem_usuario = client.post("/auth/login", json={"email": "nao@exemplo.com", "password": PASSWORD})
    assert senha_errada.status_code == sem_usuario.status_code == 401
    assert senha_errada.json() == sem_usuario.json()


def test_colaborador_barrado_em_rota_admin(client, auth):
    assert client.get("/test/admin-only", headers=auth("colab")).status_code == 403
    assert client.get("/test/admin-only", headers=auth("admin")).status_code == 200


def test_gestor_barrado_fora_do_time(client, auth, users):
    h = auth("gestor")
    assert client.get(f"/test/evaluated/{users['colab'].id}", headers=h).status_code == 200
    assert client.get(f"/test/evaluated/{users['fora'].id}", headers=h).status_code == 403


def test_colaborador_so_ve_a_si(client, auth, users):
    h = auth("colab")
    assert client.get(f"/test/evaluated/{users['colab'].id}", headers=h).status_code == 200
    assert client.get(f"/test/evaluated/{users['fora'].id}", headers=h).status_code == 403


def test_sem_consentimento_bloqueado(client, auth, users):
    h = auth("novo")
    assert client.get("/me", headers=h).status_code == 200
    assert client.get(f"/test/evaluated/{users['novo'].id}", headers=h).status_code == 403
    assert client.post("/me/consent", headers=h).json()["consented_at"] is not None
    assert client.get(f"/test/evaluated/{users['novo'].id}", headers=h).status_code == 200


def test_sem_token(client, users):
    assert client.get("/me").status_code == 401
