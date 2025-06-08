import csv
import requests

# URL do endpoint para importar produtos
url = 'http://localhost:5000/importar_produtos_csv'

# Caminho para o arquivo CSV
caminho_csv = 'caminho/para/seu/arquivo.csv'

# Função para importar produtos
def importar_produtos():
    with open(caminho_csv, mode='r', encoding='utf-8') as arquivo_csv:
        # Enviar o arquivo CSV para o endpoint
        response = requests.post(url, files={'file': arquivo_csv})
        if response.status_code == 200:
            print('Produtos importados com sucesso!')
        else:
            print(f'Erro ao importar produtos: {response.json()}')

# Executar a função
if __name__ == '__main__':
    importar_produtos()
