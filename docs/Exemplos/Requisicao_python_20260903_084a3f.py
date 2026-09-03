import requests
from bs4 import BeautifulSoup  # opcional, para extrair token do HTML

# Cria uma sessão
session = requests.Session()

# Define um User-Agent realista
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:155.0) Gecko/20100101 Firefox/155.0"
}

# 1. Acessa a página para obter o csrf token (via cookie e/ou HTML)
url_base = "http://www.cub.org.br/cub-m2-estadual/GO/"
response_get = session.get(url_base, headers=headers)

# O cookie csrftoken já está na session
# Se o token não estiver no cookie, podemos extrair do HTML:
# soup = BeautifulSoup(response_get.text, 'html.parser')
# token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
# Mas o cookie geralmente é suficiente para o Django.

# 2. Monta os dados do POST
data = {
    "csrfmiddlewaretoken": session.cookies.get("csrftoken"),  # pega do cookie
    "uf": "GO",
    "sinduscon": "10",
    "relatorio": "tabela-cub-m2",
    "ano": "2026",
    "ano_i": "2026",
    "ano_f": "2026",
    "mes": "1",
    "desoneracao": "sem-desoneracao",
    "variacao": "com-variacao",
    "cimento": "1",
    "projeto": "1"
}

# 3. Faz o POST
response_post = session.post(url_base, data=data, headers=headers)

# 4. Verifica se deu certo e salva o PDF
if response_post.status_code == 200 and "application/pdf" in response_post.headers.get("Content-Type", ""):
    # Pega o nome do arquivo do header Content-Disposition
    content_disposition = response_post.headers.get("Content-Disposition", "")
    filename = "relatorio_cub_go_2026_01.pdf"  # ou extrai do header
    if "filename=" in content_disposition:
        filename = content_disposition.split("filename=")[-1].strip('"')

    with open(filename, "wb") as f:
        f.write(response_post.content)
    print(f"PDF salvo como {filename}")
else:
    print("Falha na requisição:", response_post.status_code)
    print(response_post.text)  # pode conter mensagem de erro