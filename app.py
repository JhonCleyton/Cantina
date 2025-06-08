from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_qrcode import QRcode
from flask_cors import CORS
from flask_migrate import Migrate
import logging
from datetime import datetime, timedelta
from sqlalchemy import func
import qrcode
import io
import base64
import json
from io import BytesIO
import time
from werkzeug.utils import secure_filename
import os
import csv
import unicodedata

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banco.db'
# Removido para evitar forçar HTTPS

# Configurar diretório de uploads
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit

# Criar diretórios de upload se não existirem
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pics'), exist_ok=True)

# Configurar CORS
CORS(app)
QRcode(app)

# Configurar banco de dados e login
db = SQLAlchemy(app)  # Inicializa o objeto SQLAlchemy
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Função para formatar valores monetários
def format_currency(value):
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Registrar o filtro no Jinja2
app.jinja_env.filters['currency'] = format_currency

# Modelos
class Loja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    endereco = db.Column(db.String(200))
    telefone = db.Column(db.String(20))
    cnpj = db.Column(db.String(14), unique=True)
    ativo = db.Column(db.Boolean, default=True)
    gerente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))  # Nova coluna para associar o gerente
    
    # Relacionamentos
    produtos = db.relationship('Produto', backref='loja')
    vendas = db.relationship('Venda', backref='loja')
    categorias = db.relationship('Categoria', backref='loja', lazy=True)
    gerente = db.relationship('Usuario', foreign_keys=[gerente_id])  # Nova relação para o gerente

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    descricao = db.Column(db.String(200))
    loja_id = db.Column(db.Integer, db.ForeignKey('loja.id'), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    
    # Relacionamentos
    produtos = db.relationship('Produto', backref='categoria')

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    cpf = db.Column(db.String(11), unique=True)
    password = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # admin, gerente, vendedor, cliente
    ativo = db.Column(db.Boolean, default=True)
    saldo = db.Column(db.Float, default=0.0)
    loja_id = db.Column(db.Integer, db.ForeignKey('loja.id'))
    loja_gerenciada_id = db.Column(db.Integer, db.ForeignKey('loja.id'))
    

    # Relacionamentos
    loja = db.relationship('Loja', foreign_keys=[loja_id])
    loja_gerenciada = db.relationship('Loja', foreign_keys=[loja_gerenciada_id])
    compras = db.relationship('Venda', backref='cliente', foreign_keys='Venda.cliente_id')
    vendas_realizadas = db.relationship('Venda', backref='vendedor', foreign_keys='Venda.vendedor_id')

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text)
    preco = db.Column(db.Float, nullable=False)
    estoque = db.Column(db.Integer, default=0)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    imagem = db.Column(db.String(200))
    loja_id = db.Column(db.Integer, db.ForeignKey('loja.id'), nullable=False)
    
    # Relacionamentos
    itens_venda = db.relationship('ItemVenda', backref='produto')

class Venda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    loja_id = db.Column(db.Integer, db.ForeignKey('loja.id'), nullable=False)
    data_venda = db.Column(db.DateTime, nullable=False, default=datetime.now)
    valor_total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    
    # Relacionamentos
    itens = db.relationship('ItemVenda', backref='venda', lazy=True)

class ItemVenda(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(db.Integer, db.ForeignKey('venda.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

class Transacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)  # deposito, saque, transferencia, venda
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200))
    data = db.Column(db.DateTime, nullable=False, default=datetime.now)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    venda_id = db.Column(db.Integer, db.ForeignKey('venda.id'))
    loja_id = db.Column(db.Integer, db.ForeignKey('loja.id'))
    saldo_final = db.Column(db.Float, nullable=False)

class Notificacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    titulo = db.Column(db.String(100), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    lida = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    link = db.Column(db.String(200))  # Link opcional para redirecionar

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Rotas de Autenticação
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.tipo == 'admin':
            logger.info(f'Current user loja gerenciada ID: {current_user.loja_gerenciada_id}')
            return redirect(url_for('admin_dashboard'))
        elif current_user.tipo == 'gerente':
            # Verificar se o gerente tem loja associada
            if not current_user.loja_gerenciada:
                flash('Você não está associado a nenhuma loja como gerente. Entre em contato com o administrador.', 'warning')
                logout_user()
                return redirect(url_for('login'))
            return redirect(url_for('gerente_dashboard'))
        elif current_user.tipo == 'vendedor':
            return redirect(url_for('vendedor_dashboard'))
        else:
            return redirect(url_for('cliente_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')

        if not email or not senha:
            flash('Por favor, preencha todos os campos.', 'error')
            return redirect(url_for('login'))

        usuario = Usuario.query.filter_by(email=email).first()

        if not usuario:
            flash('Email ou senha incorretos.', 'error')
            return redirect(url_for('login'))

        if not usuario.password:
            flash('Erro no cadastro do usuário. Entre em contato com o administrador.', 'error')
            return redirect(url_for('login'))

        if check_password_hash(usuario.password, senha):
            if not usuario.ativo:
                flash('Sua conta está inativa. Entre em contato com o administrador.', 'error')
                return redirect(url_for('login'))

            # Verificar se é gerente e tem loja associada
            if usuario.tipo == 'gerente' and not usuario.loja_gerenciada:
                flash('Você não está associado a nenhuma loja como gerente. Entre em contato com o administrador.', 'warning')
                return redirect(url_for('login'))

            login_user(usuario)
            
            if usuario.tipo == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif usuario.tipo == 'gerente':
                return redirect(url_for('gerente_dashboard'))
            elif usuario.tipo == 'vendedor':
                return redirect(url_for('vendedor_dashboard'))
            else:
                return redirect(url_for('cliente_dashboard'))
        else:
            flash('Email ou senha incorretos.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Rotas do Admin
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))
    
    usuarios = Usuario.query.all()
    total_clientes = Usuario.query.filter_by(tipo='cliente').count()
    total_vendedores = Usuario.query.filter_by(tipo='vendedor').count()
    total_gerentes = Usuario.query.filter_by(tipo='gerente').count()
    total_saldo = sum(u.saldo or 0.0 for u in Usuario.query.filter_by(tipo='cliente').all())
    
    return render_template('admin/dashboard.html',
                         usuarios=usuarios,
                         total_clientes=total_clientes,
                         total_vendedores=total_vendedores,
                         total_gerentes=total_gerentes,
                         total_saldo=total_saldo)

# Rotas do Gerente
@app.route('/gerente')
@login_required
def gerente_dashboard():
    if current_user.tipo != 'gerente':
        flash('Acesso negado. Você não tem permissão para acessar esta página.', 'error')
        return redirect(url_for('login'))
    
    loja = current_user.loja_gerenciada
    if not loja:
        flash('Você não está associado a nenhuma loja como gerente. Entre em contato com o administrador.', 'warning')
        return redirect(url_for('login'))
    
    # Estatísticas da loja
    total_vendas = db.session.query(func.count(Venda.id)).filter_by(loja_id=loja.id).scalar()
    total_produtos = db.session.query(func.count(Produto.id)).filter_by(loja_id=loja.id).scalar()
    total_vendedores = db.session.query(func.count(Usuario.id)).filter_by(loja_id=loja.id, tipo='vendedor').scalar()
    
    # Vendas recentes
    vendas_recentes = Venda.query.filter_by(loja_id=loja.id).order_by(Venda.data_venda.desc()).limit(10).all()
    
    # Produtos com baixo estoque
    produtos_baixo_estoque = Produto.query.filter(
        Produto.loja_id == loja.id,
        Produto.estoque <= 10,
        Produto.ativo == True
    ).all()
    
    # Vendedores da loja
    vendedores = Usuario.query.filter_by(loja_id=loja.id, tipo='vendedor').all()
    
    return render_template('gerente/dashboard.html',
                         loja=loja,
                         total_vendas=total_vendas,
                         total_produtos=total_produtos,
                         total_vendedores=total_vendedores,
                         vendas_recentes=vendas_recentes,
                         produtos_baixo_estoque=produtos_baixo_estoque,
                         vendedores=vendedores)

@app.route('/vendedor')
@login_required
def vendedor_dashboard():
    if current_user.tipo != 'vendedor':
        return redirect(url_for('index'))
    
    try:
        # Buscar vendas do vendedor
        vendas = Venda.query.filter_by(vendedor_id=current_user.id).order_by(Venda.data_venda.desc()).all()
        
        # Calcular estatísticas
        total_vendas = len(vendas)
        valor_total_vendas = sum(venda.valor_total for venda in vendas)
        
        # Vendas do mês atual
        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        vendas_mes = Venda.query.filter(
            Venda.vendedor_id == current_user.id,
            Venda.data_venda >= primeiro_dia_mes
        ).count()

        # Buscar produtos mais vendidos
        produtos_vendidos = db.session.query(
            Produto.nome,
            func.sum(ItemVenda.quantidade).label('total_quantidade'),
            func.sum(ItemVenda.subtotal).label('total_valor')
        ).join(ItemVenda).join(Venda).filter(
            Venda.vendedor_id == current_user.id
        ).group_by(Produto.id).order_by(
            func.sum(ItemVenda.quantidade).desc()
        ).limit(5).all()

        return render_template(
            'vendedor/dashboard.html',
            vendas=vendas,
            total_vendas=total_vendas,
            valor_total_vendas=valor_total_vendas,
            vendas_mes=vendas_mes,
            produtos_vendidos=produtos_vendidos
        )
    except Exception as e:
        app.logger.error(f"Erro no dashboard do vendedor: {str(e)}")
        flash('Erro ao carregar o dashboard.', 'error')
        return redirect(url_for('index'))

@app.route('/vendedor/catalogo')
@login_required
def catalogo():
    if current_user.tipo != 'vendedor':
        return redirect(url_for('index'))
    
    if not current_user.loja:
        flash('Você não está associado a nenhuma loja.', 'warning')
        return redirect(url_for('index'))
    
    produtos = Produto.query.filter_by(loja_id=current_user.loja_id, ativo=True).all()
    clientes = Usuario.query.filter_by(tipo='cliente', ativo=True).all()
    categorias = Categoria.query.filter_by(loja_id=current_user.loja_id).all()
    
    return render_template('vendedor/catalogo.html',
                         produtos=produtos,
                         clientes=clientes,
                         categorias=categorias,
                         loja=current_user.loja)

@app.route('/venda/finalizar', methods=['POST'])
@login_required
def finalizar_venda():
    if current_user.tipo != 'vendedor':
        return jsonify({'error': 'Apenas vendedores podem finalizar vendas'}), 403
    
    try:
        data = request.get_json()
        
        if not data or 'cliente_id' not in data or 'itens' not in data:
            return jsonify({'error': 'Dados inválidos'}), 400
        
        cliente = db.session.get(Usuario, data['cliente_id'])
        if not cliente or cliente.tipo != 'cliente':
            return jsonify({'error': 'Cliente não encontrado'}), 404
        
        # Criar venda
        venda = Venda(
            cliente_id=cliente.id,
            vendedor_id=current_user.id,
            loja_id=current_user.loja_id,  # Adicionar loja_id do vendedor
            data_venda=datetime.now(),
            valor_total=0, # Inicializar com 0
            status= 'concluída_qr-code'
        )
        db.session.add(venda)
        db.session.flush()  # Obter o ID da venda
        
        # Adicionar itens
        valor_total = 0
        for item_data in data['itens']:
            produto = db.session.get(Produto, item_data['produto_id'])
            if not produto:
                return jsonify({'error': f'Produto {item_data["produto_id"]} não encontrado'}), 404
            
            quantidade = item_data['quantidade']
            preco = produto.preco
            subtotal = preco * quantidade
            
            item = ItemVenda(
                venda_id=venda.id,
                produto_id=produto.id,
                quantidade=quantidade,
                preco_unitario=preco,
                subtotal=subtotal
            )
            db.session.add(item)
            valor_total += subtotal
        
        # Atualizar valor total da venda
        venda.valor_total = valor_total
        
        db.session.commit()
        return jsonify({'message': 'Venda finalizada com sucesso', 'venda_id': venda.id})
        
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/vendedor/finalizar_venda_qr', methods=['POST'])
@login_required
def finalizar_venda_qr():
    if current_user.tipo != 'vendedor':
        return jsonify({'error': 'Acesso não autorizado'}), 403

    dados = request.json
    logging.info('Iniciando a finalização da venda com QR code.')
    logging.info(f'Dados recebidos: {dados}')
    
    cliente_id = dados.get('cliente_id')
    itens = dados.get('itens', [])
    
    if not cliente_id or not itens:
        logging.error('Dados inválidos recebidos.')
        return jsonify({'error': 'Dados inválidos'}), 400
    
    # Verificar se o cliente existe e está ativo
    cliente = db.session.get(Usuario, cliente_id)
    if not cliente or not cliente.ativo or cliente.tipo != 'cliente':
        logging.error(f'Cliente inválido: {cliente_id}')
        return jsonify({'error': 'Cliente inválido'}), 400
    
    logging.info(f'Cliente encontrado: {cliente.id}')  # Log do cliente encontrado

    # Calcular valor total e verificar estoque
    valor_total = 0
    itens_venda = []
    
    for item in itens:
        produto = db.session.get(Produto, item['id'])  # Use 'id' instead of 'produto_id'
        if not produto or not produto.ativo:
            logging.error(f'Produto inválido: {item["id"]}')
            return jsonify({'error': f'Produto {item["id"]} inválido'}), 400
        
        if produto.estoque < item['quantidade']:
            logging.error(f'Estoque insuficiente para {produto.nome}')
            return jsonify({'error': f'Estoque insuficiente para {produto.nome}'}), 400
        
        subtotal = item['quantidade'] * item['preco']  # Use 'preco' instead of 'preco_unitario'
        valor_total += subtotal
        
        itens_venda.append({
            'produto': produto,
            'quantidade': item['quantidade'],
            'preco_unitario': item['preco'],  # Here also
            'subtotal': subtotal
        })
    logging.info(f'Valor total calculado: {valor_total}')
    
    # Verificar saldo do cliente
    if cliente.saldo < valor_total:
        logging.error('Saldo insuficiente')
        return jsonify({'error': 'Saldo insuficiente'}), 400
    else:
        logging.info('Saldo suficiente para a venda.')

    try:
        # Extrair e-mail e senha do QR code
        email_cliente = dados.get('email')
        senha_cliente = dados.get('senha')

        # Verificar se o e-mail e senha são válidos
        if not email_cliente or not senha_cliente:
            logging.error('Email ou senha não fornecidos no QR code.')
            return jsonify({'error': 'Email ou senha não fornecidos'}), 400
        
        # Verificar se o cliente com esse e-mail existe e a senha bate
        cliente_com_email = db.session.query(Usuario).filter_by(email=email_cliente).first()
        if not cliente_com_email:
            logging.error(f'Cliente não encontrado para o e-mail: {email_cliente}')
            return jsonify({'error': 'Cliente não encontrado'}), 400
        
        # Aqui você pode verificar a senha de acordo com como está sendo armazenada (hash ou não)
        if not check_password_hash(cliente_com_email.senha, senha_cliente):
            logging.error(f'Senha inválida para o e-mail: {email_cliente}')
            return jsonify({'error': 'Senha inválida'}), 400

        logging.info(f'Cliente {email_cliente} autenticado com sucesso.')

        # Agora, como o login foi validado, você pode chamar a função finalizar_venda_login como se o login tivesse sido feito manualmente
        return finalizar_venda_login()
        
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        logging.error(f'Ocorreu um erro: {str(e)}')
        return jsonify({'error': 'Erro ao finalizar a venda'}), 500

@app.route('/vendedor/finalizar_venda_login', methods=['POST'])
@login_required
def finalizar_venda_login():
    if current_user.tipo != 'vendedor':
        return jsonify({'error': 'Acesso não autorizado'}), 403

    dados = request.get_json()

    app.logger.info(f'Dados recebidos: {dados}')  # Log dos dados recebidos

    # Verifique se todos os campos necessários estão presentes
    if not dados or 'cliente_id' not in dados or 'login' not in dados or 'senha' not in dados or 'itens' not in dados:
        return jsonify({'error': 'Dados inválidos'}), 400

    try:
        # Continue com a lógica de autenticação e finalização da venda...
        cliente_id = dados.get('cliente_id')
        login = dados.get('login')
        senha = dados.get('senha')
        itens = dados.get('itens')

        cliente = db.session.get(Usuario, cliente_id)
        if not cliente or cliente.tipo != 'cliente':
            return jsonify({'error': 'Cliente não encontrado'}), 404

        if not check_password_hash(cliente.password, senha):
            return jsonify({'error': 'Senha inválida'}), 400

        valor_total = 0
        itens_venda = []

        for item in itens:
            produto = db.session.get(Produto, item['id'])  # Use 'id' instead of 'produto_id'
            if not produto or not produto.ativo:
                return jsonify({'error': f'Produto {item["id"]} não encontrado ou inativo'}), 400
            
            quantidade = item['quantidade']
            preco = produto.preco
            subtotal = preco * quantidade
            
            itens_venda.append({
                'produto': produto,
                'quantidade': item['quantidade'],
                'preco_unitario': item['preco'],  # Here also
                'subtotal': subtotal
            })
            valor_total += subtotal
        
        if cliente.saldo < valor_total:
            return jsonify({'error': 'Saldo insuficiente'}), 400

        try:
            venda = Venda(
                vendedor_id=current_user.id,
                cliente_id=cliente.id,
                loja_id=current_user.loja_id,
                valor_total=valor_total,
                status='concluída_normal'
            )
            db.session.add(venda)
            db.session.flush()

            for item in itens_venda:
                item_venda = ItemVenda(
                    venda_id=venda.id,
                    produto_id=item['produto'].id,
                    quantidade=item['quantidade'],
                    preco_unitario=item['preco_unitario'],
                    subtotal=item['subtotal']
                )
                db.session.add(item_venda)

                produto.estoque -= item['quantidade']

            cliente.saldo -= valor_total
            app.logger.info(f'Saldo recuperado para o usuário {cliente.nome}: {cliente.saldo}')  # Log do saldo recuperado
            app.logger.info(f'Saldo recuperado para o usuário {cliente.nome} antes da adição: {cliente.saldo}')  # Log do saldo recuperado
            
            transacao = Transacao(
                tipo='compra',
                valor=valor_total,
                descricao=f'Compra #{venda.id}',
                saldo_final=cliente.saldo,
                usuario_id=cliente.id,
                venda_id=venda.id,
                loja_id=current_user.loja_id
            )
            db.session.add(transacao)

            db.session.commit()
            app.logger.info(f'Transação confirmada com sucesso para o usuário {cliente.nome}.')
            app.logger.info(f'Saldo final de {cliente.nome} após commit: {cliente.saldo}')
            return jsonify({
                'message': 'Venda realizada com sucesso',
                'venda_id': venda.id
            })

        except Exception as e:
            with app.app_context():
                db.session.rollback()
            app.logger.error(f'Erro ao finalizar venda: {str(e)}')
            return jsonify({'error': str(e)}), 500
        
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        app.logger.error(f'Erro ao finalizar venda: {str(e)}')
        return jsonify({'error': 'Erro interno do servidor'}), 500

# Rotas do Cliente
@app.route('/cliente/dashboard')
@login_required
def cliente_dashboard():
    if current_user.tipo != 'cliente':
        flash('Acesso não autorizado.', 'error')
        return redirect(url_for('login'))

    try:
        # Buscar compras do cliente
        compras = Venda.query.filter_by(cliente_id=current_user.id).order_by(Venda.data_venda.desc()).all()
        
        # Buscar transações do cliente
        transacoes = Transacao.query.filter_by(usuario_id=current_user.id).order_by(Transacao.data.desc()).all()
        
        # Calcular estatísticas
        total_compras = len(compras)
        valor_total_compras = sum(compra.valor_total for compra in compras)
        
        # Compras do mês atual
        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        compras_mes = Venda.query.filter(
            Venda.cliente_id == current_user.id,
            Venda.data_venda >= primeiro_dia_mes
        ).count()

        return render_template(
            'dashboard_cliente.html',
            compras=compras,
            transacoes=transacoes,
            total_compras=total_compras,
            valor_total_compras=valor_total_compras,
            compras_mes=compras_mes
        )
    except Exception as e:
        app.logger.error(f"Erro no dashboard do cliente: {str(e)}")
        flash('Erro ao carregar o dashboard.', 'error')
        return redirect(url_for('index'))

@app.route('/cliente/confirmar_venda/<int:venda_id>', methods=['POST'])
@login_required
def confirmar_venda(venda_id):
    if current_user.tipo != 'cliente':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    venda = Venda.query.get_or_404(venda_id)
    
    if venda.cliente_id != current_user.id:
        return jsonify({'error': 'Venda não pertence a este cliente'}), 403
    
    if venda.status != 'pendente':
        return jsonify({'error': 'Venda não está pendente'}), 400
    
    try:
        venda.status = 'concluída_normal'
        with app.app_context():
            db.session.commit()
        return jsonify({'message': 'Venda confirmada com sucesso'})
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/cliente/gerar_qr_code')
@login_required
def gerar_qr_code_cliente():
    if current_user.tipo != 'cliente':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    try:
        dados = {
            'id': current_user.id,
            'nome': current_user.nome,
            'email': current_user.email,
            'senha': current_user.password,  # Adicionando a senha
            'tipo': 'cliente',
            'timestamp': int(time.time())
        }
        
        if not all([dados['id'], dados['nome'], dados['email'], dados['tipo']]):
            app.logger.error('Dados para QR code estão incompletos.')
            return jsonify({'error': 'Dados inválidos para gerar QR code'}), 400

        app.logger.info(f'Gerando QR code para cliente: {dados}')
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(json.dumps(dados))
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        app.logger.info('QR code gerado com sucesso.')
        return jsonify({'qr_code': f'data:image/png;base64,{img_str}'})
        
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        app.logger.error(f'Erro ao gerar QR code: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/cliente/detalhes_compra/<int:compra_id>')
@login_required
def detalhes_compra(compra_id):
    if current_user.tipo != 'cliente':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    try:
        compra = Venda.query.filter_by(
            id=compra_id,
            cliente_id=current_user.id
        ).first()
        
        if not compra:
            return jsonify({'error': 'Compra não encontrada'}), 404
        
        itens = []
        for item in compra.itens:
            itens.append({
                'produto': {
                    'id': item.produto.id,
                    'nome': item.produto.nome
                },
                'quantidade': item.quantidade,
                'preco_unitario': item.preco_unitario,
                'subtotal': item.subtotal
            })
        
        return jsonify({
            'id': compra.id,
            'data_venda': compra.data_venda.strftime('%d/%m/%Y %H:%M'),
            'valor_total': compra.valor_total,
            'status': compra.status,
            'itens': itens
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes da compra: {str(e)}")
        return jsonify({'error': 'Erro ao buscar detalhes da compra'}), 500

@app.route('/dashboard_cliente_extrato')
@login_required
def dashboard_cliente_extrato():
    
    if current_user.tipo != 'cliente':
        flash('Acesso não autorizado.', 'error')
        return redirect(url_for('login'))

    try:
        # Buscar compras do cliente
        compras = Venda.query.filter_by(cliente_id=current_user.id).order_by(Venda.data_venda.desc()).all()
        
        # Buscar transações do cliente
        transacoes = Transacao.query.filter_by(usuario_id=current_user.id).order_by(Transacao.data.desc()).all()
        
        # Calcular estatísticas
        total_compras = len(compras)
        valor_total_compras = sum(compra.valor_total for compra in compras)
        
        # Compras do mês atual
        hoje = datetime.now()
        primeiro_dia_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        compras_mes = Venda.query.filter(
            Venda.cliente_id == current_user.id,
            Venda.data_venda >= primeiro_dia_mes
        ).count()

        return render_template(
            'dashboard_cliente_extrato.html',
            compras=compras,
            transacoes=transacoes,
            total_compras=total_compras,
            valor_total_compras=valor_total_compras,
            compras_mes=compras_mes
        )
    except Exception as e:
        app.logger.error(f"Erro no dashboard do cliente: {str(e)}")
        flash('Erro ao carregar o dashboard.', 'error')
        return redirect(url_for('index'))


@app.route('/admin/usuarios/novo', methods=['POST'])
@login_required
def novo_usuario():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Obter dados do formulário
        nome = request.form.get('nome')
        email = request.form.get('email')
        password = request.form.get('password')
        tipo = request.form.get('tipo')
        cpf = request.form.get('cpf')
        loja_id = request.form.get('loja_id')
        
        # Validar dados obrigatórios
        if not all([nome, email, password, tipo, cpf]):
            flash('Todos os campos obrigatórios devem ser preenchidos', 'danger')
            return redirect(url_for('gerenciar_usuarios'))
        
        # Verificar se email já existe
        if Usuario.query.filter_by(email=email).first():
            flash('Email já cadastrado', 'danger')
            return redirect(url_for('gerenciar_usuarios'))
        
        # Verificar se CPF já existe
        if Usuario.query.filter_by(cpf=cpf).first():
            flash('CPF já cadastrado', 'danger')
            return redirect(url_for('gerenciar_usuarios'))
        
        # Criar novo usuário
        usuario = Usuario(
            nome=nome,
            email=email,
            password=generate_password_hash(password),
            tipo=tipo,
            cpf=cpf,
            loja_id=loja_id if loja_id else None,
            ativo=True,
            saldo=0.0
        )
        
        with app.app_context():
            db.session.add(usuario)
            db.session.commit()
        
        flash('Usuário cadastrado com sucesso!', 'success')
        return redirect(url_for('gerenciar_usuarios'))
        
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        logger.error(f"Erro ao cadastrar usuário: {str(e)}")
        flash('Erro ao cadastrar usuário', 'danger')
        return redirect(url_for('gerenciar_usuarios'))

@app.route('/')
def index():
    return redirect(url_for('login'))

# Rotas de Administração de Saldo
@app.route('/admin/adicionar_saldo/<int:usuario_id>', methods=['POST'])
@login_required
def adicionar_saldo(usuario_id):
    if current_user.tipo != 'admin':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    try:
        # Tentar obter dados do JSON primeiro
        if request.is_json:
            data = request.get_json()
        else:
            # Se não for JSON, pegar do form data
            data = request.form

        valor = float(data.get('valor', 0))
        descricao = data.get('descricao', 'Adição de saldo')
        
        if valor <= 0:
            return jsonify({'error': 'Valor inválido'}), 400
        
        usuario = db.session.get(Usuario, usuario_id)
        if not usuario:
            return jsonify({'error': 'Usuário não encontrado'}), 404

        app.logger.info(f'Adicionando saldo para o usuário {usuario.nome}...')
        app.logger.info(f'Saldo atual de {usuario.nome}: {usuario.saldo}')
        
        usuario.saldo += valor
        app.logger.info(f'Saldo atualizado para {usuario.nome}: {usuario.saldo} (antes do commit)')
        db.session.commit()
        app.logger.info(f'Transação confirmada. Saldo final de {usuario.nome}: {usuario.saldo}')
        
        transacao = Transacao(
            tipo='entrada',
            valor=valor,
            descricao=descricao,
            saldo_final=usuario.saldo,
            usuario_id=usuario.id
        )
        
        with app.app_context():
            db.session.add(transacao)
            db.session.commit()
        
        app.logger.info(f'Saldo adicionado com sucesso para o usuário {usuario.nome}!')
        return jsonify({
            'message': f'Saldo adicionado com sucesso para {usuario.nome}',
            'novo_saldo': usuario.saldo
        })
        
    except (ValueError, TypeError) as e:
        return jsonify({'error': 'Dados inválidos'}), 400
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        app.logger.error(f"Erro ao adicionar saldo: {str(e)}")
        return jsonify({'error': 'Erro ao adicionar saldo'}), 500

@app.route('/admin/carteiras')
@login_required
def gerenciar_carteiras():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))
    
    usuarios = Usuario.query.filter_by(tipo='cliente').all()
    return render_template('admin/carteiras.html', usuarios=usuarios)

@app.route('/admin/usuarios')
@login_required
def gerenciar_usuarios():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))
    
    usuarios = Usuario.query.all()
    lojas = Loja.query.filter_by(ativo=True).all()
    return render_template('admin/usuarios.html', usuarios=usuarios, lojas=lojas)

@app.route('/admin/usuario/<int:id>/ativar', methods=['POST'])
@login_required
def ativar_usuario(id):
    if current_user.tipo != 'admin':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    usuario = db.session.get(Usuario, id)
    usuario.ativo = True
    with app.app_context():
        db.session.commit()
    return jsonify({'message': 'Usuário ativado com sucesso'})

@app.route('/admin/usuario/<int:id>/desativar', methods=['POST'])
@login_required
def desativar_usuario(id):
    if current_user.tipo != 'admin':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    usuario = db.session.get(Usuario, id)
    usuario.ativo = False
    with app.app_context():
        db.session.commit()
    return jsonify({'message': 'Usuário desativado com sucesso'})

@app.route('/admin/usuario/<int:id>/transacoes')
@login_required
def historico_transacoes(id):
    if current_user.tipo != 'admin':
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    usuario = db.session.get(Usuario, id)
    transacoes = [{
        'data': t.data.isoformat(),
        'tipo': t.tipo,
        'valor': float(t.valor),
        'descricao': t.descricao,
        'saldo_final': float(t.saldo_final)
    } for t in usuario.transacoes]
    
    return jsonify({'transacoes': transacoes})

@app.route('/admin/editar-usuario/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))
    
    usuario = db.session.get(Usuario, id)
    
    if request.method == 'POST':
        usuario.nome = request.form.get('nome')
        usuario.email = request.form.get('email')
        usuario.tipo = request.form.get('tipo')
        usuario.cpf = request.form.get('cpf')
        usuario.matricula = request.form.get('matricula')
        
        if request.form.get('password'):
            usuario.password = generate_password_hash(request.form.get('password'))
        
        with app.app_context():
            db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('gerenciar_usuarios'))
    
    return render_template('admin/editar_usuario.html', usuario=usuario)

# Rotas do Catálogo
@app.route('/admin/categorias', methods=['GET', 'POST'])
@login_required
def gerenciar_categorias():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        loja_id = request.form.get('loja_id')
        
        if not loja_id:
            flash('Por favor, selecione uma loja.', 'error')
            return redirect(url_for('gerenciar_categorias'))
        
        categoria = Categoria(nome=nome, descricao=descricao, loja_id=loja_id)
        with app.app_context():
            db.session.add(categoria)
            db.session.commit()
        
        flash('Categoria criada com sucesso!', 'success')
        return redirect(url_for('gerenciar_categorias'))
    
    categorias = Categoria.query.all()
    lojas = Loja.query.filter_by(ativo=True).all()
    return render_template('admin/categorias.html', categorias=categorias, lojas=lojas)

@app.route('/admin/produtos', methods=['GET', 'POST'])
@login_required
def gerenciar_produtos():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        preco = float(request.form.get('preco'))
        estoque = int(request.form.get('estoque'))
        categoria_id = int(request.form.get('categoria_id'))
        imagem_url = request.form.get('imagem_url')
        
        produto = Produto(
            nome=nome,
            descricao=descricao,
            preco=preco,
            estoque=estoque,
            categoria_id=categoria_id,
            imagem=imagem_url,  # Corrigido para usar o campo correto
            loja_id=current_user.loja_id
        )
        with app.app_context():
            db.session.add(produto)
            db.session.commit()
        
        flash('Produto criado com sucesso!', 'success')
        return redirect(url_for('gerenciar_produtos'))
    
    produtos = Produto.query.all()
    categorias = Categoria.query.all()
    return render_template('admin/produtos.html', produtos=produtos, categorias=categorias)

# Rotas de Relatórios
@app.route('/admin/relatorios')
@login_required
def relatorios():
    if current_user.tipo != 'admin':
        flash('Acesso não autorizado.', 'danger')
        return redirect(url_for('login'))
    
    vendas = Venda.query.all()
    total_vendas = len(vendas)
    valor_total_vendas = sum(venda.valor_total for venda in vendas)
    
    # Vendas por vendedor
    vendas_por_vendedor = db.session.query(
        Usuario.nome,
        db.func.count(Venda.id).label('total_vendas'),
        db.func.sum(Venda.valor_total).label('valor_total')
    ).join(Venda, Usuario.id == Venda.vendedor_id
    ).group_by(Usuario.id).all()
    
    # Produtos mais vendidos
    produtos_mais_vendidos = db.session.query(
        Produto.nome,
        db.func.sum(ItemVenda.quantidade).label('quantidade_vendida'),
        db.func.sum(ItemVenda.subtotal).label('valor_total')
    ).join(ItemVenda
    ).group_by(Produto.id
    ).order_by(db.func.sum(ItemVenda.quantidade).desc()
    ).limit(10).all()
    
    return render_template('admin/relatorios.html',
                         total_vendas=total_vendas,
                         valor_total_vendas=valor_total_vendas,
                         vendas_por_vendedor=vendas_por_vendedor,
                         produtos_mais_vendidos=produtos_mais_vendidos)

@app.route('/gerar_qr_code/<int:usuario_id>')
@login_required
def gerar_qr_code(usuario_id):
    if current_user.id != usuario_id and current_user.tipo != 'admin':
        flash('Acesso não autorizado', 'error')
        return redirect(url_for('index'))
    
    usuario = db.session.get(Usuario, usuario_id)
    dados_qr = {
        'id': usuario.id,
        'nome': usuario.nome,
        'tipo': usuario.tipo
    }
    
    # Gerar QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(str(dados_qr))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_str = base64.b64encode(img_buffer.getvalue()).decode()
    
    return jsonify({
        'qr_code': img_str,
        'usuario': dados_qr
    })

@app.route('/venda/<int:venda_id>')
@login_required
def ver_venda(venda_id):
    venda = Venda.query.get_or_404(venda_id)
    
    # Verificar se o usuário tem permissão para ver a venda
    if current_user.tipo == 'cliente' and venda.cliente_id != current_user.id:
        abort(403)
    elif current_user.tipo == 'vendedor' and venda.vendedor_id != current_user.id:
        abort(403)
    
    itens = ItemVenda.query.filter_by(venda_id=venda.id).all()
    
    return render_template('venda/detalhes.html',
                         venda=venda,
                         itens=itens)

@app.route('/venda/<int:venda_id>/detalhes')
@login_required
def detalhes_venda(venda_id):
    try:
        venda = Venda.query.get_or_404(venda_id)
        
        # Verificar se o usuário tem permissão para ver os detalhes
        if current_user.tipo not in ['admin', 'gerente'] and current_user.id != venda.cliente_id:
            return jsonify({'error': 'Acesso não autorizado'}), 403
        
        # Buscar itens da venda
        itens = []
        for item in ItemVenda.query.filter_by(venda_id=venda.id).all():
            produto = db.session.get(Produto, item.produto_id)
            itens.append({
                'produto': {
                    'id': produto.id,
                    'nome': produto.nome,
                    'preco': float(produto.preco)
                },
                'quantidade': item.quantidade,
                'preco_unitario': float(item.preco_unitario),
                'subtotal': float(item.subtotal)
            })
        
        # Buscar informações da loja e vendedor
        loja = Loja.query.get(venda.loja_id)
        vendedor = db.session.get(Usuario, venda.vendedor_id)
        
        return jsonify({
            'id': venda.id,
            'data_venda': venda.data_venda.isoformat(),
            'valor_total': float(venda.valor_total),
            'status': venda.status,
            'loja': {
                'id': loja.id,
                'nome': loja.nome
            },
            'vendedor': {
                'id': vendedor.id,
                'nome': vendedor.nome
            },
            'itens': itens
        })
    
    except Exception as e:
        app.logger.error(f"Erro ao buscar detalhes da venda: {str(e)}")
        return jsonify({'error': 'Erro ao buscar detalhes da venda'}), 500

# Rotas de Gerenciamento de Lojas
@app.route('/admin/lojas')
@login_required
def gerenciar_lojas():
    if current_user.tipo != 'admin':
        return redirect(url_for('index'))
    
    # Buscar lojas com contagem de produtos e vendedores
    lojas = Loja.query.all()
    
    # Para cada loja, buscar contagens
    for loja in lojas:
        # Contagem de produtos ativos
        loja.produtos_count = Produto.query.filter_by(loja_id=loja.id, ativo=True).count()
        # Contagem de vendedores ativos
        loja.vendedores_count = Usuario.query.filter_by(loja_id=loja.id, tipo='vendedor', ativo=True).count()
        # Contagem de vendas
        loja.vendas_count = Venda.query.filter_by(loja_id=loja.id).count()
    
    gerentes = Usuario.query.filter_by(tipo='gerente').all()
    return render_template('admin/lojas.html', lojas=lojas, gerentes=gerentes)

@app.route('/admin/lojas/nova', methods=['POST'])
@login_required
def nova_loja():
    if current_user.tipo != 'admin':
        return redirect(url_for('index'))
    
    nome = request.form.get('nome')
    endereco = request.form.get('endereco')
    telefone = request.form.get('telefone')
    cnpj = request.form.get('cnpj')
    gerente_id = request.form.get('gerente_id')  # Nova linha para associar o gerente
    
    # Criar nova loja
    loja = Loja(
        nome=nome,
        endereco=endereco,
        telefone=telefone,
        cnpj=cnpj,
        gerente_id=gerente_id  # Nova linha para associar o gerente
    )
    with app.app_context():
        db.session.add(loja)
        db.session.commit()
    
    flash('Loja criada com sucesso!', 'success')
    return redirect(url_for('gerenciar_lojas'))

@app.route('/admin/lojas/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_loja(id):
    if current_user.tipo != 'admin':
        return redirect(url_for('index'))
    
    loja = Loja.query.get_or_404(id)
    
    if request.method == 'POST':
        loja.nome = request.form.get('nome')
        loja.endereco = request.form.get('endereco')
        loja.telefone = request.form.get('telefone')
        loja.cnpj = request.form.get('cnpj')
        gerente_id = request.form.get('gerente_id')
        if not gerente_id:
            flash('Selecione um gerente válido.', 'danger')
            return redirect(url_for('editar_loja', id=id))
        gerente = db.session.get(Usuario, gerente_id)
        if not gerente or gerente.tipo != 'gerente':
            flash('Gerente inválido.', 'danger')
            return redirect(url_for('editar_loja', id=id))
        loja.gerente_id = gerente_id
        gerente.loja_gerenciada_id = loja.id  # Associar a loja ao gerente
        
        with app.app_context():
            db.session.commit()
        flash('Loja atualizada com sucesso!', 'success')
        return redirect(url_for('gerenciar_lojas'))
    
    gerentes = Usuario.query.filter_by(tipo='gerente').all()
    return render_template('admin/editar_loja.html', loja=loja, gerentes=gerentes)

@app.route('/gerente/vendedores')
@login_required
def gerenciar_vendedores_loja():
    if current_user.tipo != 'gerente':
        return redirect(url_for('index'))
    
    loja = current_user.loja_gerenciada
    if not loja:
        flash('Você não está associado a nenhuma loja.', 'warning')
        return redirect(url_for('index'))
    
    vendedores = Usuario.query.filter_by(loja_id=loja.id, tipo='vendedor').all()
    return render_template('gerente/vendedores.html', vendedores=vendedores, loja=loja)

@app.route('/gerente/produtos')
@login_required
def gerenciar_produtos_loja():
    if current_user.tipo != 'gerente':
        return redirect(url_for('index'))
    
    loja = current_user.loja_gerenciada
    if not loja:
        flash('Você não está associado a nenhuma loja.', 'warning')
        return redirect(url_for('index'))
    
    produtos = Produto.query.filter_by(loja_id=loja.id).all()
    categorias = Categoria.query.filter_by(loja_id=loja.id).all()
    return render_template('gerente/produtos.html', 
                         produtos=produtos, 
                         categorias=categorias, 
                         loja=loja)

@app.route('/gerente/relatorios')
@login_required
def relatorios_loja():
    if current_user.tipo != 'gerente':
        return redirect(url_for('index'))
    
    try:
        # Obter a loja do gerente
        loja = current_user.loja_gerenciada
        if not loja:
            flash('Gerente não está associado a uma loja', 'danger')
            return redirect(url_for('index'))
        
        # Calcular datas para filtros
        hoje = datetime.now()
        inicio_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        inicio_ano = hoje.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Obter vendas da loja
        vendas = Venda.query.filter_by(loja_id=loja.id).order_by(Venda.data_venda.desc()).all()
        
        # Calcular estatísticas
        total_vendas = len(vendas)
        vendas_mes = sum(1 for v in vendas if v.data_venda >= inicio_mes)
        valor_total = sum(v.valor_total for v in vendas)
        valor_mes = sum(v.valor_total for v in vendas if v.data_venda >= inicio_mes)
        
        # Obter produtos mais vendidos
        produtos_vendidos = db.session.query(
            Produto.id,
            Produto.nome,
            func.sum(ItemVenda.quantidade).label('total_vendido'),
            func.sum(ItemVenda.subtotal).label('valor_total')
        ).join(ItemVenda).join(Venda).filter(
            Venda.loja_id == loja.id
        ).group_by(
            Produto.id
        ).order_by(
            func.sum(ItemVenda.quantidade).desc()
        ).limit(10).all()
        
        # Obter vendedores mais produtivos
        vendedores = db.session.query(
            Usuario.id,
            Usuario.nome,
            func.count(Venda.id).label('total_vendas'),
            func.sum(Venda.valor_total).label('valor_total')
        ).join(Venda, Usuario.id == Venda.vendedor_id).filter(
            Venda.loja_id == loja.id
        ).group_by(
            Usuario.id
        ).order_by(
            func.count(Venda.id).desc()
        ).all()
        
        return render_template('gerente/relatorios.html',
                             loja=loja,
                             vendas=vendas,
                             total_vendas=total_vendas,
                             vendas_mes=vendas_mes,
                             valor_total=valor_total,
                             valor_mes=valor_mes,
                             produtos_vendidos=produtos_vendidos,
                             vendedores=vendedores,
                             inicio_mes=inicio_mes,
                             inicio_ano=inicio_ano)
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatórios: {str(e)}")
        flash('Erro ao gerar relatórios', 'danger')
        return redirect(url_for('gerente_dashboard'))

# Rotas de Notificações
@app.route('/notificacoes')
@login_required
def listar_notificacoes():
    notificacoes = Notificacao.query.filter_by(usuario_id=current_user.id)\
        .order_by(Notificacao.data_criacao.desc())\
        .limit(10)\
        .all()
    return render_template('notificacoes.html', notificacoes=notificacoes)

@app.route('/notificacoes/nao-lidas')
@login_required
def get_notificacoes_nao_lidas():
    notificacoes = Notificacao.query.filter_by(
        usuario_id=current_user.id,
        lida=False
    ).order_by(Notificacao.data_criacao.desc()).all()
    
    return jsonify([{
        'id': n.id,
        'titulo': n.titulo,
        'mensagem': n.mensagem,
        'tipo': n.tipo,
        'data': n.data_criacao.strftime('%d/%m/%Y %H:%M'),
        'link': n.link
    } for n in notificacoes])

@app.route('/notificacoes/<int:id>/marcar-como-lida', methods=['POST'])
@login_required
def marcar_notificacao_como_lida(id):
    notificacao = Notificacao.query.get_or_404(id)
    if notificacao.usuario_id != current_user.id:
        return jsonify({'success': False, 'message': 'Acesso não autorizado'}), 403
    
    notificacao.lida = True
    with app.app_context():
        db.session.commit()
    return jsonify({'success': True})

def criar_notificacao(usuario_id, titulo, mensagem, tipo='info', link=None):
    """Função auxiliar para criar notificações"""
    notificacao = Notificacao(
        usuario_id=usuario_id,
        titulo=titulo,
        mensagem=mensagem,
        tipo=tipo,
        link=link
    )
    with app.app_context():
        db.session.add(notificacao)
        db.session.commit()
    return notificacao

@app.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html')

@app.route('/perfil/editar', methods=['POST'])
@login_required
def editar_perfil():
    try:
        # Dados básicos
        current_user.nome = request.form.get('nome')
        current_user.email = request.form.get('email')
        current_user.bio = request.form.get('bio')
        
        # Endereço
        current_user.endereco = request.form.get('endereco')
        current_user.cidade = request.form.get('cidade')
        current_user.estado = request.form.get('estado')
        current_user.cep = request.form.get('cep')
        
        # Preferências
        current_user.tema_escuro = request.form.get('tema_escuro') == 'on'
        current_user.notificacoes_email = request.form.get('notificacoes_email') == 'on'
        
        # Foto de perfil
        foto = request.files.get('foto_perfil')
        if foto and foto.filename:
            # Verificar extensão
            ext = os.path.splitext(foto.filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                return jsonify({'success': False, 'message': 'Formato de arquivo não suportado'}), 400
            
            # Gerar nome único para o arquivo
            filename = secure_filename(f"{current_user.id}_{int(time.time())}{ext}")
            
            # Caminho completo do arquivo
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pics', filename)
            
            # Remover foto antiga se existir
            if current_user.foto_perfil:
                old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pics', current_user.foto_perfil)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            
            # Salvar nova foto
            foto.save(filepath)
            current_user.foto_perfil = filename
        
        # Senha (opcional)
        nova_senha = request.form.get('nova_senha')
        if nova_senha:
            senha_atual = request.form.get('senha_atual')
            if not check_password_hash(current_user.password, senha_atual):
                return jsonify({'success': False, 'message': 'Senha atual incorreta'}), 400
            current_user.password = generate_password_hash(nova_senha)
        
        with app.app_context():
            db.session.commit()
        
        # Criar notificação
        criar_notificacao(
            current_user.id,
            "Perfil atualizado",
            "Suas informações de perfil foram atualizadas com sucesso!",
            "success"
        )
        
        return jsonify({'success': True, 'message': 'Perfil atualizado com sucesso!'})
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        logger.error(f"Erro ao atualizar perfil: {str(e)}")
        return jsonify({'success': False, 'message': 'Erro ao atualizar perfil'}), 500

@app.route('/gerente/vendedores/novo', methods=['POST'])
@login_required

def novo_vendedor():
    if current_user.tipo != 'gerente':
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('index'))
        
    try:
        # Obter dados do formulário
        nome = request.form.get('nome')
        email = request.form.get('email')
        cpf = request.form.get('cpf')
        
        # Definir senha inicial
        password = '123456'
        
        # Validar dados obrigatórios
        if not all([nome, email, password, cpf]):
            flash('Todos os campos obrigatórios devem ser preenchidos', 'danger')
            return redirect(url_for('gerenciar_vendedores_loja'))
        
        # Verificar se email já existe
        if Usuario.query.filter_by(email=email).first():
            flash('Email já cadastrado', 'danger')
            return redirect(url_for('gerenciar_vendedores_loja'))
        
        # Verificar se CPF já existe
        if Usuario.query.filter_by(cpf=cpf).first():
            flash('CPF já cadastrado', 'danger')
            return redirect(url_for('gerenciar_vendedores_loja'))
        
        # Criar novo vendedor
        vendedor = Usuario(
            nome=nome,
            email=email,
            password=generate_password_hash(password),
            tipo='vendedor',
            cpf=cpf,
            ativo=True,
            saldo=0.0,  # Inicializar saldo com 0
            loja_id=current_user.loja_gerenciada.id  # Associar à loja do gerente
        )
        
        with app.app_context():
            db.session.add(vendedor)
            db.session.commit()
        
        flash('Vendedor cadastrado com sucesso!', 'success')
        return redirect(url_for('gerenciar_vendedores_loja'))
        
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        logger.error(f"Erro ao cadastrar vendedor: {str(e)}")
        flash('Erro ao cadastrar vendedor', 'danger')
        return redirect(url_for('gerenciar_vendedores_loja'))

@app.route('/gerente/produtos/novo', methods=['POST'])
@login_required
def novo_produto():
    if current_user.tipo != 'gerente':
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('index'))
        
    try:
        # Obter dados do formulário
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        preco = float(request.form.get('preco').replace('R$', '').replace('.', '').replace(',', '.'))
        estoque = int(request.form.get('quantidade'))  # Recebe como quantidade mas salva como estoque
        categoria_id = request.form.get('categoria')
        
        # Processar imagem
        tipo_imagem = request.form.get('tipo_imagem')
        imagem_url = None
        
        if tipo_imagem == 'upload':
            imagem = request.files.get('imagem')
            if imagem and imagem.filename:
                # Verificar extensão
                ext = os.path.splitext(imagem.filename)[1].lower()
                if ext not in ['.jpg', '.jpeg', '.png']:
                    flash('Formato de imagem não suportado', 'danger')
                    return redirect(url_for('gerenciar_produtos_loja'))
                
                # Gerar nome único para o arquivo
                imagem_filename = secure_filename(f"produto_{int(time.time())}{ext}")
                
                # Salvar imagem
                imagem_path = os.path.join(app.config['UPLOAD_FOLDER'], 'produtos', imagem_filename)
                os.makedirs(os.path.dirname(imagem_path), exist_ok=True)
                imagem.save(imagem_path)
                imagem_url = imagem_filename
        else:  # tipo_imagem == 'url'
            imagem_url = request.form.get('imagem_url')
        
        # Criar novo produto
        produto = Produto(
            nome=nome,
            descricao=descricao,
            preco=preco,
            estoque=estoque,
            categoria_id=categoria_id,
            imagem=imagem_url,  # Corrigido para usar o campo correto
            loja_id=current_user.loja_gerenciada.id
        )
        
        with app.app_context():
            db.session.add(produto)
            db.session.commit()
        
        flash('Produto cadastrado com sucesso!', 'success')
        return redirect(url_for('gerenciar_produtos_loja'))
        
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        logger.error(f"Erro ao cadastrar produto: {str(e)}")
        flash('Erro ao cadastrar produto', 'danger')
        return redirect(url_for('gerenciar_produtos_loja'))

@app.route('/gerente/categorias_loja', methods=['GET', 'POST'])
@login_required
def gerenciar_categorias_loja():
    if current_user.tipo != 'gerente':
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        try:
            nome = request.form.get('nome')
            descricao = request.form.get('descricao')
            
            # Criar nova categoria associada à loja do gerente
            categoria = Categoria(
                nome=nome,
                descricao=descricao,
                loja_id=current_user.loja_gerenciada.id  # Associar à loja do gerente
            )
            
            with app.app_context():
                db.session.add(categoria)
                db.session.commit()
            
            flash('Categoria criada com sucesso!', 'success')
            return redirect(url_for('gerenciar_categorias_loja'))
            
        except Exception as e:
            with app.app_context():
                db.session.rollback()
            logger.error(f"Erro ao criar categoria: {str(e)}")
            flash('Erro ao criar categoria', 'danger')
            return redirect(url_for('gerenciar_categorias_loja'))
    
    # Buscar categorias da loja
    categorias = Categoria.query.filter_by(loja_id=current_user.loja_gerenciada.id).all()
    return render_template('gerente/categorias.html', categorias=categorias)

@app.route('/gerente/produtos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_produto(id):
    if current_user.tipo != 'gerente':
        flash('Acesso não autorizado', 'danger')
        return redirect(url_for('index'))
        
    produto = db.session.get(Produto, id)
    
    # Verificar se o produto pertence à loja do gerente
    if produto.loja_id != current_user.loja_gerenciada.id:
        flash('Produto não pertence à sua loja', 'danger')
        return redirect(url_for('gerenciar_produtos'))
    
    if request.method == 'POST':
        try:
            # Obter dados do formulário
            nome = request.form.get('nome')
            descricao = request.form.get('descricao')
            preco = float(request.form.get('preco').replace('R$', '').replace('.', '').replace(',', '.'))
            estoque = int(request.form.get('quantidade'))  # Recebe como quantidade mas salva como estoque
            categoria_id = request.form.get('categoria')
            
            # Processar imagem
            tipo_imagem = request.form.get('tipo_imagem')
            
            if tipo_imagem == 'upload':
                imagem = request.files.get('imagem')
                if imagem and imagem.filename:
                    # Verificar extensão
                    ext = os.path.splitext(imagem.filename)[1].lower()
                    if ext not in ['.jpg', '.jpeg', '.png']:
                        flash('Formato de imagem não suportado', 'danger')
                        return redirect(url_for('editar_produto', id=id))
                    
                    # Gerar nome único para o arquivo
                    imagem_filename = secure_filename(f"produto_{int(time.time())}{ext}")
                    
                    # Salvar imagem
                    imagem_path = os.path.join(app.config['UPLOAD_FOLDER'], 'produtos', imagem_filename)
                    os.makedirs(os.path.dirname(imagem_path), exist_ok=True)
                    imagem.save(imagem_path)
                    produto.imagem = imagem_filename
            elif tipo_imagem == 'url':
                imagem_url = request.form.get('imagem_url')
                if imagem_url:
                    produto.imagem = imagem_url
            
            # Atualizar produto
            produto.nome = nome
            produto.descricao = descricao
            produto.preco = preco
            produto.estoque = estoque
            produto.categoria_id = categoria_id
            
            with app.app_context():
                db.session.commit()
            
            flash('Produto atualizado com sucesso!', 'success')
            return redirect(url_for('gerenciar_produtos'))
            
        except Exception as e:
            with app.app_context():
                db.session.rollback()
            logger.error(f"Erro ao atualizar produto: {str(e)}")
            flash('Erro ao atualizar produto', 'danger')
            return redirect(url_for('editar_produto', id=id))
    
    categorias = Categoria.query.filter_by(loja_id=current_user.loja_gerenciada.id).all()
    return render_template('gerente/editar_produto.html', 
                         produto=produto, 
                         categorias=categorias)

@app.route('/gerente/produtos/<int:produto_id>/excluir', methods=['POST'])
@login_required
def excluir_produto(produto_id):
    produto = db.session.get(Produto, produto_id)
    if produto:
        with app.app_context():
            db.session.delete(produto)
            db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Produto não encontrado.'}), 404

def verificar_gerente_associado(loja_id):
    loja = Loja.query.get(loja_id)
    if loja and loja.gerente_id:
        return True  # Loja tem um gerente associado
    return False  # Loja não tem gerente associado

@app.route('/verificar_gerente/<int:loja_id>')
@login_required
def verificar_gerente(loja_id):
    tem_gerente = verificar_gerente_associado(loja_id)
    if tem_gerente:
        return f'A loja com ID {loja_id} tem um gerente associado.'
    else:
        return f'A loja com ID {loja_id} não tem gerente associado.'

def verificar_gerentes():
    with app.app_context():
        gerentes = Usuario.query.filter_by(tipo='gerente').all()
        for gerente in gerentes:
            print(f'ID: {gerente.id}, Nome: {gerente.nome}, Loja Gerenciada ID: {gerente.loja_gerenciada_id}')

def atualizar_loja_gerenciada():
    with app.app_context():
        gerentes = Usuario.query.filter_by(tipo='gerente', loja_gerenciada_id=None).all()
        for gerente in gerentes:
            gerente.loja_gerenciada_id = 1  # Atualizando para a loja com ID 2
        db.session.commit()  # Salvar as alterações

@app.route('/admin/atribuir_loja_gerente', methods=['GET', 'POST'])
@login_required
def atribuir_loja_gerente():
    if current_user.tipo != 'admin':
        flash('Acesso negado. Apenas administradores podem acessar esta página.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        gerente_id = request.form.get('gerente_id')
        loja_id = request.form.get('loja_id')
        
        gerente = Usuario.query.get(gerente_id)
        loja = Loja.query.get(loja_id)
        
        if not gerente or gerente.tipo != 'gerente':
            flash('Gerente inválido.', 'danger')
            return redirect(url_for('atribuir_loja_gerente'))
            
        if not loja:
            flash('Loja inválida.', 'danger')
            return redirect(url_for('atribuir_loja_gerente'))
        
        # Verifica se o gerente já tem uma loja
        if gerente.loja_gerenciada_id:
            flash('Este gerente já está associado a uma loja.', 'warning')
            return redirect(url_for('atribuir_loja_gerente'))
            
        # Verifica se a loja já tem um gerente
        if loja.gerente_id:
            flash('Esta loja já tem um gerente associado.', 'warning')
            return redirect(url_for('atribuir_loja_gerente'))
        
        # Atribui a loja ao gerente
        gerente.loja_gerenciada_id = loja.id
        loja.gerente_id = gerente.id
        
        try:
            db.session.commit()
            flash('Loja atribuída ao gerente com sucesso!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atribuir loja: {str(e)}', 'danger')
        
        return redirect(url_for('atribuir_loja_gerente'))
    
    # GET: Mostrar formulário
    # Buscar todos os gerentes, independente de terem ou não loja atribuída
    todos_gerentes = Usuario.query.filter_by(tipo='gerente').all()
    lojas_sem_gerente = Loja.query.filter_by(gerente_id=None).all()
    
    # Buscar gerentes com loja atribuída para a tabela
    gerentes_com_loja = db.session.query(Usuario).join(Loja, Usuario.loja_gerenciada_id == Loja.id)\
                             .filter(Usuario.tipo == 'gerente')\
                             .filter(Usuario.loja_gerenciada_id.isnot(None))\
                             .all()
    
    # Criar lista de dicionários com as informações necessárias para a tabela
    gerentes_lojas = []
    for gerente in gerentes_com_loja:
        gerentes_lojas.append({
            'nome': gerente.nome,
            'email': gerente.email,
            'loja_nome': gerente.loja_gerenciada.nome if gerente.loja_gerenciada else 'Nenhuma',
            'loja_cnpj': gerente.loja_gerenciada.cnpj if gerente.loja_gerenciada else 'N/A',
            'id': gerente.id
        })
    
    return render_template('admin/atribuir_loja_gerente.html', 
                         gerentes=todos_gerentes, 
                         lojas=lojas_sem_gerente,
                         gerentes_lojas=gerentes_lojas)

@app.route('/catalogo_cliente')
@login_required
def catalogo_cliente():
    lojas = Loja.query.all()  # Busca todas as lojas
    return render_template('catalogo.html', lojas=lojas)

@app.route('/loja/<int:loja_id>/produtos', methods=['GET'])
@login_required
def ver_produtos(loja_id):
    categoria_id = request.args.get('categoria_id')  # Obtém a categoria selecionada
    if categoria_id:
        produtos = Produto.query.filter_by(loja_id=loja_id, categoria_id=categoria_id).all()  # Filtra produtos pela categoria
    else:
        produtos = Produto.query.filter_by(loja_id=loja_id).all()  # Busca todos os produtos da loja
    categorias = Categoria.query.filter_by(loja_id=loja_id).all()  # Busca as categorias da loja
    loja = Loja.query.get(loja_id)  # Busca a loja correspondente
    return render_template('produtos.html', produtos=produtos, categorias=categorias, loja=loja)
    
@app.route('/importar_produtos_csv', methods=['POST'])
@login_required
def importar_produtos_csv():
    if current_user.tipo != 'admin':  # Verifica se o usuário é um administrador
        return jsonify({'error': 'Acesso não autorizado'}), 403

    arquivo = request.files['file']  # O arquivo CSV deve ser enviado no corpo da requisição
    if not arquivo:
        return jsonify({'error': 'Nenhum arquivo enviado.'}), 400

    try:
        reader = csv.DictReader(arquivo.stream.read().decode('utf-8').splitlines())
        for linha in reader:
            nome = linha['nome']
            descricao = linha['descricao']
            preco = float(linha['preco'])
            estoque = int(linha['estoque'])
            categoria_nome = linha['categoria']
            url_imagem = linha['url_imagem']

            # Verificar se a categoria existe ou criar uma nova
            categoria = db.session.query(Categoria).filter_by(nome=categoria_nome).first()
            if not categoria:
                categoria = Categoria(nome=categoria_nome)
                with app.app_context():
                    db.session.add(categoria)
                    db.session.commit()

            # Criar o produto
            produto = Produto(
                nome=nome,
                descricao=descricao,
                preco=preco,
                estoque=estoque,
                categoria=categoria,
                imagem=url_imagem
            )
            with app.app_context():
                db.session.add(produto)
                db.session.commit()

        return jsonify({'message': 'Produtos importados com sucesso!'}), 200
    except Exception as e:
        with app.app_context():
            db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/clientes', methods=['GET'])
@login_required
def listar_clientes():
    nome = request.args.get('nome')  # Recebe o nome para filtragem
    if nome:
        clientes = Usuario.query.filter(Usuario.nome.ilike(f'%{nome}%')).all()
    else:
        clientes = Usuario.query.filter_by(tipo='cliente').all()  # Retorna todos os clientes
    return render_template('clientes.html', clientes=clientes)  # Renderiza uma página com a lista de clientes

@app.route('/finalizar_venda_select', methods=['POST'])
@login_required
def finalizar_venda_select():
    cliente_id = request.form.get('cliente_id')  # Recebe o ID do cliente selecionado
    itens = request.form.getlist('itens')  # Recebe a lista de itens da venda

    # Verifica se o cliente existe
    cliente = Usuario.query.get(cliente_id)
    if not cliente:
        return jsonify({'error': 'Cliente não encontrado.'}), 404

    # Chama a função de finalização de venda com o cliente selecionado
    return finalizar_venda(cliente, itens)  # Chama a função de finalização de venda que você já tem implementada

@app.route('/finalizar_venda_select_v2', methods=['POST'])
def finalizar_venda_select_v2():
    data = request.get_json()
    cliente_id = data.get('cliente_id')
    itens = data.get('itens')
    
    # Lógica para finalizar a venda com o cliente_id e itens
    # Exemplo: salvar a venda no banco de dados
    
    return jsonify({'message': 'Venda finalizada com sucesso!'}), 200

import logging

@app.route('/obter_credenciais_cliente/<int:cliente_id>', methods=['GET'])
def obter_credenciais_cliente(cliente_id):
    logging.info(f"Tentando obter credenciais para cliente_id: {cliente_id}")
    try:
        cliente = Usuario.query.get(cliente_id)  # Supondo que 'Usuario' é seu modelo de cliente
        if cliente:
            logging.info(f"Cliente encontrado: {cliente.email}")
            return jsonify({'email': cliente.email, 'password': cliente.password}), 200
        else:
            logging.warning(f"Cliente não encontrado para cliente_id: {cliente_id}")
            return jsonify({'error': 'Cliente não encontrado!'}), 404
    except Exception as e:
        logging.error(f"Erro ao obter credenciais: {str(e)}")
        return jsonify({'error': str(e)}), 500  # Retornar erro interno do servidor

@app.route('/vendedor/validar_login', methods=['POST'])
def validar_login():
    dados = request.get_json()
    email = dados.get('email')
    senha = dados.get('senha')

    cliente = Usuario.query.filter_by(email=email).first()
    if not cliente or not check_password_hash(cliente.password, senha):
        return jsonify({'error': 'Senha incorreta'}), 401

    return jsonify({'message': 'Login válido'}), 200

def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')


if __name__ == '__main__':
    with app.app_context():
        atualizar_loja_gerenciada()  # Chama a função para atualizar a loja gerenciada
        # Criar todas as tabelas
        db.create_all()
        
        # Criar loja padrão se não existir
        if not Loja.query.first():
            loja_padrao = Loja(
                nome='Loja Matriz',
                endereco='Rua Principal, 123',
                telefone='11999999999',
                cnpj='12345678901234',
                ativo=True
            )
            db.session.add(loja_padrao)
            db.session.commit()
            
            # Criar usuário admin se não existir
            if not Usuario.query.filter_by(email='admin@cantina.com').first():
                admin = Usuario(
                    nome='Administrador',
                    email='admin@cantina.com',
                    cpf='12345678901',
                    password=generate_password_hash('admin2025'),
                    tipo='admin',
                    ativo=True
                )
                db.session.add(admin)
                db.session.commit()
    
    app.run(
        host='0.0.0.0',
        port=3100,
        debug=True
    )
