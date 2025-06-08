from OpenSSL import crypto
import os

def gerar_certificado():
    # Gerar chave privada
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    # Criar certificado
    cert = crypto.X509()
    cert.get_subject().C = "BR"
    cert.get_subject().ST = "Estado"
    cert.get_subject().L = "Cidade"
    cert.get_subject().O = "Sistema Bancario"
    cert.get_subject().CN = "localhost"
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365*24*60*60)  # Válido por 1 ano
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')

    # Salvar certificado e chave
    with open("cert.pem", "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
    with open("key.pem", "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

if __name__ == '__main__':
    gerar_certificado()
    print("Certificado gerado com sucesso!")
