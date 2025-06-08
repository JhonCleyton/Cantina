from app import db, app, Produto, Categoria, Loja
from sqlalchemy import text

# Criar uma categoria padrão para cada loja
def migrate_db():
    with app.app_context():
        # Primeiro, vamos adicionar a coluna categoria_id
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE produto ADD COLUMN categoria_id INTEGER REFERENCES categoria(id)'))
            conn.commit()
        
        # Agora vamos criar uma categoria padrão para cada loja
        lojas = Loja.query.all()
        for loja in lojas:
            # Criar categoria padrão
            categoria_padrao = Categoria(
                nome='Geral',
                descricao='Categoria padrão para produtos existentes',
                loja_id=loja.id
            )
            db.session.add(categoria_padrao)
            db.session.commit()
            
            # Atualizar produtos existentes para usar a categoria padrão
            produtos = Produto.query.filter_by(loja_id=loja.id).all()
            for produto in produtos:
                produto.categoria_id = categoria_padrao.id
            
            db.session.commit()
            print(f'Migração concluída para a loja {loja.nome}')

if __name__ == '__main__':
    migrate_db()
