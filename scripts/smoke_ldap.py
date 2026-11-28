"""Valida credenciais contra OpenLDAP real e 401/403 com Redis real."""
import time

import httpx

BASE = "http://127.0.0.1:8000"


def login_retry(client, username, password, timeout=75):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        response = client.post(BASE + "/api/auth/login",
                               json={"username": username, "password": password})
        if response.status_code == 503:
            time.sleep(3)
            continue
        return response
    raise AssertionError("LDAP indisponível por mais de 75 segundos")


def main():
    with httpx.Client(timeout=15) as client:
        front = client.get(BASE + "/")
        assert front.status_code == 200
        assert 'id="loginForm"' in front.text, "Formulário LDAP visual ausente"
        assert 'id="checkRole"' in front.text, "Demonstração HTTP 403 ausente"
        assert 'id="logout"' in front.text, "Logout visual ausente"
        assert "/api/auth/login" in front.text
        assert "/api/auth/me" in front.text
        assert "/api/professor/stats/courses" in front.text
        assert "Kerberos ainda não implementado" in front.text
        assert client.get(BASE + "/api/professor/questions/sample-didatico-01/answer").status_code == 401
        invalid = login_retry(client, "estudante", "senha-errada")
        assert invalid.status_code == 401, f"Credencial inválida: {invalid.status_code} {invalid.text}"
        student = login_retry(client, "estudante", "demo123")
        assert student.status_code == 200, f"LDAP estudante: {student.status_code} {student.text}"
        assert student.json()["role"] == "estudante"
        assert client.get(BASE + "/api/auth/me").json()["role"] == "estudante"
        assert client.get(BASE + "/api/professor/questions/sample-didatico-01/answer").status_code == 403
        assert client.get(BASE + "/api/professor/stats/courses").status_code == 403
        assert client.post(BASE + "/api/auth/logout").status_code == 200
        assert client.get(BASE + "/api/auth/me").status_code == 401
        teacher = login_retry(client, "professor", "demo123")
        assert teacher.status_code == 200, f"LDAP professor: {teacher.status_code} {teacher.text}"
        assert teacher.json()["role"] == "professor"
        answer = client.get(BASE + "/api/professor/questions/sample-didatico-01/answer")
        assert answer.status_code == 200, f"LDAP professor answer: {answer.status_code} {answer.text}"
        assert "answer" in answer.json()
        assert client.get(BASE + "/api/professor/stats/courses").status_code == 200
        print("LDAP OpenLDAP REAL + interface de login: login + 401/403 + professor: OK")


if __name__ == "__main__":
    main()
