from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timedelta

# Gerar chave privada
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)

# Criar certificado autoassinado
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, u"localhost")
])

cert = x509.CertificateBuilder().subject_name(
    subject
).issuer_name(
    issuer
).public_key(
    private_key.public_key()
).serial_number(
    x509.random_serial_number()
).not_valid_before(
    datetime.utcnow()
).not_valid_after(
    datetime.utcnow() + timedelta(days=365)
).add_extension(
    x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
    critical=False
).sign(private_key, hashes.SHA256())

# Salvar chave privada
with open("key.pem", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))

# Salvar certificado
with open("cert.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))
