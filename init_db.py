from app import app, db, Usuario, Loja, Produto, Venda, ItemVenda, Transacao
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def init_db():
    with app.app_context():
        # Criar as tabelas
        db.create_all()

        # Criar loja padrão
        loja = Loja(
            nome='Loja Matriz',
            endereco='Rua Principal, 123',
            telefone='11999999999',
            cnpj='12345678901234',
            ativo=True
        )
        db.session.add(loja)
        db.session.commit()

        # Criar usuários
        usuarios = [
            {
                'nome': 'Administrador',
                'email': 'admin@admin.com',
                'password': generate_password_hash('admin'),
                'cpf': '12345678901',
                'tipo': 'admin',
                'ativo': True,
                'saldo': 0.0
            },
            {
                'nome': 'Vendedor Teste',
                'email': 'vendedor@teste.com',
                'password': generate_password_hash('123456'),
                'cpf': '23456789012',
                'tipo': 'vendedor',
                'ativo': True,
                'saldo': 0.0
            },
            {
                'nome': 'Cliente Teste',
                'email': 'cliente@teste.com',
                'password': generate_password_hash('123456'),
                'cpf': '34567890123',
                'tipo': 'cliente',
                'ativo': True,
                'saldo': 1000.0
            }
        ]

        for user_data in usuarios:
            usuario = Usuario(**user_data)
            db.session.add(usuario)
        db.session.commit()

        # Criar produtos
        produtos = [
            {
                'nome': 'Produto 1',
                'descricao': 'Descrição do Produto 1',
                'preco': 100.0,
                'estoque': 50,
                'loja_id': loja.id,
                'ativo': True
            },
            {
                'nome': 'Produto 2',
                'descricao': 'Descrição do Produto 2',
                'preco': 200.0,
                'estoque': 30,
                'loja_id': loja.id,
                'ativo': True
            }
        ]

        for prod_data in produtos:
            produto = Produto(**prod_data)
            db.session.add(produto)
        db.session.commit()

        # Criar algumas vendas de exemplo
        cliente = Usuario.query.filter_by(tipo='cliente').first()
        vendedor = Usuario.query.filter_by(tipo='vendedor').first()
        produtos = Produto.query.all()

        for i in range(5):
            venda = Venda(
                cliente_id=cliente.id,
                vendedor_id=vendedor.id,
                loja_id=loja.id,
                data_venda=datetime.now() - timedelta(days=i),
                valor_total=0,
                status='concluída_login'
            )
            db.session.add(venda)
            db.session.commit()

            valor_total = 0
            for produto in produtos:
                item = ItemVenda(
                    venda_id=venda.id,
                    produto_id=produto.id,
                    quantidade=1,
                    preco_unitario=produto.preco,
                    subtotal=produto.preco
                )
                db.session.add(item)
                valor_total += produto.preco

            venda.valor_total = valor_total
            db.session.commit()

            # Criar transação para a venda
            transacao = Transacao(
                usuario_id=cliente.id,
                tipo='compra',
                valor=valor_total * -1,
                data=venda.data_venda,
                descricao=f'Compra na {loja.nome}',
                saldo_final=cliente.saldo - valor_total
            )
            db.session.add(transacao)
            cliente.saldo -= valor_total
            db.session.commit()

        print('Banco de dados inicializado com sucesso!')

if __name__ == '__main__':
    init_db()
