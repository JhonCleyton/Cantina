from app import db

def upgrade():
    # Adicionar coluna metodo_pagamento
    db.engine.execute('ALTER TABLE venda ADD COLUMN metodo_pagamento VARCHAR(20) NOT NULL DEFAULT "normal"')

def downgrade():
    # Remover coluna metodo_pagamento
    db.engine.execute('ALTER TABLE venda DROP COLUMN metodo_pagamento')

if __name__ == '__main__':
    upgrade()
