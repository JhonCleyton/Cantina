from app import app, db
from app import Usuario, Loja, Categoria  # Importar os modelos
from sqlalchemy import text  # Importar a função text

# Remover tabelas manualmente
with app.app_context():
    db.reflect()  # Refletir o banco de dados atual
    db.session.execute(text('DROP TABLE IF EXISTS usuario'))  # Remover a tabela usuario
    db.session.execute(text('DROP TABLE IF EXISTS loja'))  # Remover a tabela loja
    db.session.execute(text('DROP TABLE IF EXISTS categoria'))  # Remover a tabela categoria
    db.session.commit()  # Confirmar as alterações