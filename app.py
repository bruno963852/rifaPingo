from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from sqlalchemy import inspect, text
import os
from datetime import datetime
import smtplib
import random
import json
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import re
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'rifa-key-2024-seguro')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rifa.db'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Criar pasta de uploads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Configuracoes de email SMTP
EMAIL_FROM = os.getenv('EMAIL_FROM', os.getenv('EMAIL_ADDRESS', 'seu_email@gmail.com'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', EMAIL_FROM)
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', os.getenv('EMAIL_PASSWORD', 'sua_senha'))
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.resend.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
APP_PORT = int(os.getenv('PORT', 5000))
DEBUG_MODE = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
PINGO_IMAGE_PATH = os.path.join(app.root_path, 'static', 'images', 'pingo.jpg')

# Configuração de admin
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'senha123')
TOTAL_NUMEROS_RIFA = 200

# Extensões de arquivo permitidas
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def carregar_lista_json(valor):
    if not valor:
        return []
    try:
        itens = json.loads(valor)
        return itens if isinstance(itens, list) else []
    except (TypeError, ValueError):
        return []

def salvar_lista_json(itens):
    return json.dumps(itens, ensure_ascii=True)

def novo_lote(prefixo):
    return f'{prefixo}_{uuid.uuid4().hex}'

# Decorator para proteger rotas admin
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Modelo de Banco de Dados
class Participante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120))
    email = db.Column(db.String(120), nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    quantidade_tickets = db.Column(db.Integer, nullable=False)
    comprovante = db.Column(db.String(255), nullable=False)
    comprovantes = db.Column(db.Text)
    status = db.Column(db.String(20), default='pendente')  # pendente, aprovado, rejeitado
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_aprovacao = db.Column(db.DateTime)
    numeros_sorte = db.Column(db.String(500))  # string com números separados por vírgula
    motivo_rejeicao = db.Column(db.String(255))
    quantidade_tickets_pendente = db.Column(db.Integer)
    comprovante_pendente = db.Column(db.String(255))
    comprovantes_pendente = db.Column(db.Text)
    data_solicitacao_extra = db.Column(db.DateTime)
    motivo_rejeicao_pendente = db.Column(db.String(255))
    lote_cadastro = db.Column(db.String(64))
    lote_pendente = db.Column(db.String(64))
    historico_comprovantes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<Participante {self.email}>'

def garantir_colunas_participante():
    inspector = inspect(db.engine)
    colunas_existentes = {coluna['name'] for coluna in inspector.get_columns('participante')}
    colunas_necessarias = {
        'nome': 'VARCHAR(120)',
        'comprovantes': 'TEXT',
        'quantidade_tickets_pendente': 'INTEGER',
        'comprovante_pendente': 'VARCHAR(255)',
        'comprovantes_pendente': 'TEXT',
        'data_solicitacao_extra': 'DATETIME',
        'motivo_rejeicao_pendente': 'VARCHAR(255)',
        'lote_cadastro': 'VARCHAR(64)',
        'lote_pendente': 'VARCHAR(64)',
        'historico_comprovantes': 'TEXT'
    }

    with db.engine.begin() as conexao:
        for nome, definicao in colunas_necessarias.items():
            if nome not in colunas_existentes:
                conexao.execute(text(f'ALTER TABLE participante ADD COLUMN {nome} {definicao}'))

# Criar tabelas
with app.app_context():
    db.create_all()
    garantir_colunas_participante()

# Função para enviar email
def enviar_email(destinatario, assunto, corpo_html):
    try:
        msg = MIMEMultipart('related')
        msg['Subject'] = assunto
        msg['From'] = EMAIL_FROM
        msg['To'] = destinatario

        alternativa = MIMEMultipart('alternative')
        parte_html = MIMEText(corpo_html, 'html')
        alternativa.attach(parte_html)
        msg.attach(alternativa)

        if os.path.exists(PINGO_IMAGE_PATH):
            with open(PINGO_IMAGE_PATH, 'rb') as image_file:
                imagem = MIMEImage(image_file.read())
                imagem.add_header('Content-ID', '<pingo-photo>')
                imagem.add_header('Content-Disposition', 'inline', filename='pingo.jpg')
                msg.attach(imagem)

        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.starttls()

        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, destinatario, msg.as_string())
        server.quit()
        return True, None
    except Exception as e:
        app.logger.exception('Erro ao enviar email para %s', destinatario)
        return False, str(e)

def obter_numeros_lista(participante):
    if not participante.numeros_sorte:
        return []
    return sorted(int(numero.strip()) for numero in participante.numeros_sorte.split(',') if numero.strip())

def formatar_numeros(numeros):
    return ','.join(map(str, sorted(numeros)))

def possui_solicitacao_extra_pendente(participante):
    return bool(
        participante.quantidade_tickets_pendente and (
            participante.comprovante_pendente or participante.comprovantes_pendente
        )
    )

def total_numeros_confirmados():
    return sum(
        participante.quantidade_tickets
        for participante in Participante.query.filter_by(status='aprovado').all()
    )

def total_numeros_pendentes():
    cadastros_iniciais = sum(
        participante.quantidade_tickets
        for participante in Participante.query.filter_by(status='pendente').all()
    )
    compras_adicionais = sum(
        participante.quantidade_tickets_pendente or 0
        for participante in Participante.query.filter_by(status='aprovado').all()
        if participante.quantidade_tickets_pendente
    )
    return cadastros_iniciais + compras_adicionais

def numeros_disponiveis():
    return TOTAL_NUMEROS_RIFA - total_numeros_confirmados() - total_numeros_pendentes()

def salvar_comprovante(email, arquivo, prefixo='cadastro'):
    filename = secure_filename(f"{prefixo}_{email}_{datetime.now().timestamp()}_{arquivo.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    arquivo.save(filepath)
    return filename

def salvar_comprovantes(email, arquivos, prefixo='cadastro'):
    return [salvar_comprovante(email, arquivo, prefixo=prefixo) for arquivo in arquivos]

def obter_arquivos_upload(campo):
    return [arquivo for arquivo in request.files.getlist(campo) if arquivo and arquivo.filename]

def obter_comprovantes_campo(participante, campo_lista, campo_legado):
    comprovantes = []

    for item in carregar_lista_json(getattr(participante, campo_lista) or ''):
        if isinstance(item, str):
            comprovantes.append(item)
        elif isinstance(item, dict) and item.get('arquivo'):
            comprovantes.append(item['arquivo'])

    if not comprovantes and getattr(participante, campo_legado, None):
        comprovantes.append(getattr(participante, campo_legado))

    return comprovantes

def obter_historico_comprovantes(participante):
    historico = []
    vistos = set()
    for item in carregar_lista_json(participante.historico_comprovantes or ''):
        if isinstance(item, dict) and item.get('arquivo'):
            chave = (
                item.get('arquivo'),
                item.get('tipo', ''),
                item.get('status', ''),
                item.get('lote_id', '')
            )
            if chave not in vistos:
                historico.append(item)
                vistos.add(chave)

    if historico:
        return historico

    fallback = []
    for arquivo in obter_comprovantes_campo(participante, 'comprovantes', 'comprovante'):
        fallback.append({
            'arquivo': arquivo,
            'tipo': 'cadastro_inicial',
            'status': participante.status,
            'lote_id': participante.lote_cadastro or 'legado_cadastro',
            'data_envio': participante.data_criacao.isoformat() if participante.data_criacao else ''
        })

    for arquivo in obter_comprovantes_campo(participante, 'comprovantes_pendente', 'comprovante_pendente'):
        fallback.append({
            'arquivo': arquivo,
            'tipo': 'compra_adicional',
            'status': 'pendente',
            'lote_id': participante.lote_pendente or 'legado_pendente',
            'data_envio': participante.data_solicitacao_extra.isoformat() if participante.data_solicitacao_extra else ''
        })

    return fallback

def adicionar_comprovantes_historico(participante, arquivos, tipo, status, lote_id):
    historico = obter_historico_comprovantes(participante)
    data_envio = datetime.utcnow().isoformat()
    existentes = {
        (
            item.get('arquivo'),
            item.get('tipo', ''),
            item.get('status', ''),
            item.get('lote_id', '')
        )
        for item in historico
    }
    for arquivo in arquivos:
        chave = (arquivo, tipo, status, lote_id)
        if chave in existentes:
            continue
        historico.append({
            'arquivo': arquivo,
            'tipo': tipo,
            'status': status,
            'lote_id': lote_id,
            'data_envio': data_envio
        })
        existentes.add(chave)
    participante.historico_comprovantes = salvar_lista_json(historico)

def atualizar_status_lote_historico(participante, lote_id, novo_status):
    if not lote_id:
        return

    historico = obter_historico_comprovantes(participante)
    alterado = False
    for item in historico:
        if item.get('lote_id') == lote_id:
            item['status'] = novo_status
            alterado = True

    if alterado:
        participante.historico_comprovantes = salvar_lista_json(historico)

def serializar_comprovantes_admin(participante, comprovantes):
    itens = []
    for item in comprovantes:
        if isinstance(item, str):
            item = {'arquivo': item}

        arquivo = item.get('arquivo')
        if not arquivo:
            continue

        itens.append({
            'arquivo': arquivo,
            'tipo': item.get('tipo', ''),
            'status': item.get('status', ''),
            'url': url_for('visualizar_comprovante_arquivo', participante_id=participante.id, filename=arquivo)
        })

    return itens

def numeros_disponiveis_para_edicao(quantidade_atual):
    return numeros_disponiveis() + (quantidade_atual or 0)

def montar_resultado_consulta(participante, senha='', mensagem=None, mensagem_tipo='sucesso'):
    numeros = [str(numero) for numero in obter_numeros_lista(participante)]
    resultado = {
        'status': participante.status,
        'nome': participante.nome or '',
        'email': participante.email,
        'senha': senha,
        'quantidade_tickets': participante.quantidade_tickets,
        'numeros_sorte': numeros,
        'data_aprovacao': participante.data_aprovacao.strftime('%d/%m/%Y %H:%M') if participante.data_aprovacao else '',
        'solicitacao_extra_pendente': possui_solicitacao_extra_pendente(participante),
        'quantidade_tickets_pendente': participante.quantidade_tickets_pendente or 0,
        'motivo_rejeicao_pendente': participante.motivo_rejeicao_pendente
    }

    if mensagem:
        resultado['mensagem_extra'] = mensagem
        resultado['mensagem_extra_tipo'] = mensagem_tipo

    return resultado

# Função para gerar números da sorte únicos
def gerar_numeros_sorte(quantidade):
    # Buscar todos os números já usados
    participantes_aprovados = Participante.query.filter_by(status='aprovado').all()
    numeros_usados = set()
    
    for p in participantes_aprovados:
        if p.numeros_sorte:
            numeros = p.numeros_sorte.split(',')
            numeros_usados.update(int(n.strip()) for n in numeros)
    
    # Encontrar números disponíveis
    numeros_disponiveis = [n for n in range(1, TOTAL_NUMEROS_RIFA + 1) if n not in numeros_usados]
    
    # Se não houver números suficientes, retornar vazio
    if len(numeros_disponiveis) < quantidade:
        return None
    
    numeros_sorte = random.sample(numeros_disponiveis, quantidade)
    return ','.join(map(str, sorted(numeros_sorte)))

# Rotas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    confirmados = total_numeros_confirmados()
    em_espera = total_numeros_pendentes()
    total_bloqueado = confirmados + em_espera
    bloqueado = True if total_bloqueado >= TOTAL_NUMEROS_RIFA else False
    
    return jsonify({
        'confirmados': confirmados,
        'em_espera': em_espera,
        'total': total_bloqueado,
        'bloqueado': bloqueado
    })

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').lower().strip()
        senha = request.form.get('senha', '').strip()
        quantidade_str = request.form.get('quantidade_tickets', '0')
        
        # Validações
        if not nome:
            return jsonify({'sucesso': False, 'mensagem': 'Nome é obrigatório'}), 400

        if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({'sucesso': False, 'mensagem': 'Email inválido'}), 400
        
        if not senha or len(senha) < 6:
            return jsonify({'sucesso': False, 'mensagem': 'Senha deve ter no mínimo 6 caracteres'}), 400
        
        try:
            quantidade = int(quantidade_str)
            if quantidade < 1 or quantidade > TOTAL_NUMEROS_RIFA:
                return jsonify({'sucesso': False, 'mensagem': f'Quantidade deve ser entre 1 e {TOTAL_NUMEROS_RIFA}'}), 400
        except ValueError:
            return jsonify({'sucesso': False, 'mensagem': 'Quantidade inválida'}), 400

        if quantidade > numeros_disponiveis():
            return jsonify({'sucesso': False, 'mensagem': 'Não há números disponíveis suficientes para essa quantidade.'}), 400
        
        # Verificar se email já existe e está ativo
        participante_existente = Participante.query.filter_by(email=email).first()
        if participante_existente and participante_existente.status != 'rejeitado':
            return jsonify({'sucesso': False, 'mensagem': 'Este email já foi cadastrado'}), 400
        
        # Se o cadastro anterior foi rejeitado, remover e criar novo
        if participante_existente and participante_existente.status == 'rejeitado':
            db.session.delete(participante_existente)
            db.session.commit()
        
        arquivos = obter_arquivos_upload('comprovante')
        if not arquivos:
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo foi enviado'}), 400

        for arquivo in arquivos:
            if not allowed_file(arquivo.filename):
                return jsonify({'sucesso': False, 'mensagem': 'Tipo de arquivo não permitido. Use: PDF, PNG, JPG, GIF, BMP'}), 400

        lote_cadastro = novo_lote('cadastro')
        filenames = salvar_comprovantes(email, arquivos)
        
        # Criar participante
        participante = Participante(
            nome=nome,
            email=email,
            senha=senha,
            quantidade_tickets=quantidade,
            comprovante=filenames[0],
            comprovantes=salvar_lista_json(filenames),
            status='pendente'
        )
        participante.lote_cadastro = lote_cadastro
        adicionar_comprovantes_historico(participante, filenames, 'cadastro_inicial', 'pendente', lote_cadastro)
        db.session.add(participante)
        db.session.commit()
        
        return jsonify({'sucesso': True, 'mensagem': 'Cadastro realizado com sucesso! Aguarde a aprovação.'}), 201
    
    return render_template('cadastro.html')

@app.route('/consultar', methods=['GET', 'POST'])
def consultar():
    resultado = None
    
    if request.method == 'POST':
        acao = request.form.get('acao', 'consultar')
        email = request.form.get('email', '').lower().strip()
        senha = request.form.get('senha', '').strip()
        
        if not email or not senha:
            resultado = {'erro': 'Digite email e senha'}
            return render_template('consultar.html', resultado=resultado)
        
        participante = Participante.query.filter_by(email=email).first()
        
        if not participante:
            resultado = {'erro': 'Nenhum cadastro encontrado'}
        elif participante.senha != senha:
            resultado = {'erro': 'Senha incorreta'}
        elif acao == 'adicionar_numeros':
            if participante.status != 'aprovado':
                resultado = {'erro': 'Somente cadastros aprovados podem solicitar novos números.'}
            elif possui_solicitacao_extra_pendente(participante):
                resultado = montar_resultado_consulta(
                    participante,
                    senha=senha,
                    mensagem='Você já possui uma solicitação adicional aguardando aprovação.',
                    mensagem_tipo='alerta'
                )
            else:
                quantidade_extra_str = request.form.get('quantidade_tickets_extra', '0')
                try:
                    quantidade_extra = int(quantidade_extra_str)
                    if quantidade_extra < 1 or quantidade_extra > TOTAL_NUMEROS_RIFA:
                        raise ValueError
                except ValueError:
                    resultado = montar_resultado_consulta(
                        participante,
                        senha=senha,
                        mensagem=f'A quantidade adicional deve ser entre 1 e {TOTAL_NUMEROS_RIFA}.',
                        mensagem_tipo='erro'
                    )
                    return render_template('consultar.html', resultado=resultado)

                if quantidade_extra > numeros_disponiveis():
                    resultado = montar_resultado_consulta(
                        participante,
                        senha=senha,
                        mensagem='Não há números disponíveis suficientes para essa solicitação.',
                        mensagem_tipo='erro'
                    )
                elif not obter_arquivos_upload('comprovante'):
                    resultado = montar_resultado_consulta(
                        participante,
                        senha=senha,
                        mensagem='Envie o novo comprovante PIX para solicitar mais números.',
                        mensagem_tipo='erro'
                    )
                else:
                    arquivos = obter_arquivos_upload('comprovante')
                    if any(not allowed_file(arquivo.filename) for arquivo in arquivos):
                        resultado = montar_resultado_consulta(
                            participante,
                            senha=senha,
                            mensagem='Tipo de arquivo não permitido. Use: PDF, PNG, JPG, GIF, BMP.',
                            mensagem_tipo='erro'
                        )
                    else:
                        lote_pendente = novo_lote('extra')
                        filenames = salvar_comprovantes(email, arquivos, prefixo='extra')
                        participante.quantidade_tickets_pendente = quantidade_extra
                        participante.comprovante_pendente = filenames[0]
                        participante.comprovantes_pendente = salvar_lista_json(filenames)
                        participante.data_solicitacao_extra = datetime.utcnow()
                        participante.motivo_rejeicao_pendente = None
                        participante.lote_pendente = lote_pendente
                        adicionar_comprovantes_historico(participante, filenames, 'compra_adicional', 'pendente', lote_pendente)
                        db.session.commit()
                        resultado = montar_resultado_consulta(
                            participante,
                            senha=senha,
                            mensagem='Solicitação enviada com sucesso. Aguarde a aprovação dos novos números.',
                            mensagem_tipo='sucesso'
                        )
        elif participante.status == 'pendente':
            resultado = {'status': 'pendente', 'mensagem': 'Seu cadastro está aguardando aprovação'}
        elif participante.status == 'rejeitado':
            resultado = {
                'status': 'rejeitado', 
                'mensagem': f'Seu cadastro foi rejeitado. Motivo: {participante.motivo_rejeicao}',
                'email': participante.email
            }
        elif participante.status == 'aprovado':
            resultado = montar_resultado_consulta(participante, senha=senha)
    
    return render_template('consultar.html', resultado=resultado)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        senha = request.form.get('senha', '')
        if senha == ADMIN_PASSWORD:
            session['admin_logged'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('admin_login.html', erro='Senha incorreta')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged', None)
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@app.route('/api/admin/participantes')
@login_required
def get_participantes():
    status_filter = request.args.get('status', 'pendente')
    participantes = []

    if status_filter == 'pendente':
        for participante in Participante.query.filter_by(status='pendente').all():
            comprovantes = [
                {
                    'arquivo': arquivo,
                    'tipo': 'cadastro_inicial',
                    'status': 'pendente'
                }
                for arquivo in obter_comprovantes_campo(participante, 'comprovantes', 'comprovante')
            ]
            participantes.append({
                'id': participante.id,
                'nome': participante.nome,
                'email': participante.email,
                'quantidade_tickets': participante.quantidade_tickets,
                'comprovantes': serializar_comprovantes_admin(participante, comprovantes),
                'data_criacao': participante.data_criacao.strftime('%d/%m/%Y %H:%M'),
                'numeros_sorte': participante.numeros_sorte,
                'tipo_solicitacao': 'cadastro_inicial',
                'tipo_label': 'Cadastro inicial',
                'pode_editar_quantidade': True
            })

        for participante in Participante.query.filter_by(status='aprovado').all():
            if possui_solicitacao_extra_pendente(participante):
                comprovantes = [
                    {
                        'arquivo': arquivo,
                        'tipo': 'compra_adicional',
                        'status': 'pendente'
                    }
                    for arquivo in obter_comprovantes_campo(participante, 'comprovantes_pendente', 'comprovante_pendente')
                ]
                participantes.append({
                    'id': participante.id,
                    'nome': participante.nome,
                    'email': participante.email,
                    'quantidade_tickets': participante.quantidade_tickets_pendente,
                    'comprovantes': serializar_comprovantes_admin(participante, comprovantes),
                    'data_criacao': participante.data_solicitacao_extra.strftime('%d/%m/%Y %H:%M') if participante.data_solicitacao_extra else '',
                    'numeros_sorte': participante.numeros_sorte,
                    'tipo_solicitacao': 'compra_adicional',
                    'tipo_label': 'Compra adicional',
                    'pode_editar_quantidade': True
                })

        participantes.sort(key=lambda item: item['data_criacao'], reverse=True)
    else:
        for participante in Participante.query.filter_by(status=status_filter).all():
            participantes.append({
                'id': participante.id,
                'nome': participante.nome,
                'email': participante.email,
                'quantidade_tickets': participante.quantidade_tickets,
                'comprovantes': serializar_comprovantes_admin(participante, obter_historico_comprovantes(participante)),
                'data_criacao': participante.data_criacao.strftime('%d/%m/%Y %H:%M'),
                'numeros_sorte': participante.numeros_sorte,
                'tipo_solicitacao': 'cadastro_inicial',
                'tipo_label': 'Cadastro inicial',
                'pode_editar_quantidade': status_filter == 'pendente'
            })
    
    return jsonify(participantes)

@app.route('/api/admin/participantes/<int:participante_id>', methods=['PATCH'])
@login_required
def atualizar_participante_admin(participante_id):
    participante = Participante.query.get_or_404(participante_id)
    data = request.get_json() or {}
    tipo_solicitacao = data.get('tipo_solicitacao', 'cadastro_inicial')

    nome = data.get('nome')
    if nome is not None:
        nome = nome.strip()
        if not nome:
            return jsonify({'sucesso': False, 'mensagem': 'Nome é obrigatório'}), 400
        participante.nome = nome

    quantidade_informada = data.get('quantidade_tickets')
    if quantidade_informada is not None:
        try:
            quantidade = int(quantidade_informada)
        except (TypeError, ValueError):
            return jsonify({'sucesso': False, 'mensagem': 'Quantidade inválida'}), 400

        if quantidade < 1 or quantidade > TOTAL_NUMEROS_RIFA:
            return jsonify({'sucesso': False, 'mensagem': f'Quantidade deve ser entre 1 e {TOTAL_NUMEROS_RIFA}'}), 400

        if tipo_solicitacao == 'cadastro_inicial' and participante.status == 'pendente':
            if quantidade > numeros_disponiveis_para_edicao(participante.quantidade_tickets):
                return jsonify({'sucesso': False, 'mensagem': 'Não há números disponíveis suficientes para essa quantidade.'}), 400
            participante.quantidade_tickets = quantidade
        elif tipo_solicitacao == 'compra_adicional' and possui_solicitacao_extra_pendente(participante):
            if quantidade > numeros_disponiveis_para_edicao(participante.quantidade_tickets_pendente):
                return jsonify({'sucesso': False, 'mensagem': 'Não há números disponíveis suficientes para essa quantidade.'}), 400
            participante.quantidade_tickets_pendente = quantidade
        else:
            return jsonify({'sucesso': False, 'mensagem': 'A quantidade só pode ser alterada em solicitações pendentes.'}), 400

    if nome is None and quantidade_informada is None:
        return jsonify({'sucesso': False, 'mensagem': 'Nenhuma alteração foi informada'}), 400

    db.session.commit()
    return jsonify({'sucesso': True, 'mensagem': 'Dados atualizados com sucesso.'})

@app.route('/api/admin/aprovar/<int:participante_id>', methods=['POST'])
@login_required
def aprovar_participante(participante_id):
    participante = Participante.query.get_or_404(participante_id)

    aprovacao_adicional = possui_solicitacao_extra_pendente(participante) and participante.status == 'aprovado'

    if participante.status == 'pendente':
        quantidade_aprovada = participante.quantidade_tickets
    elif aprovacao_adicional:
        quantidade_aprovada = participante.quantidade_tickets_pendente
    else:
        return jsonify({'sucesso': False, 'mensagem': 'Participante não está pendente'}), 400

    numeros_sorte = gerar_numeros_sorte(quantidade_aprovada)

    if not numeros_sorte:
        return jsonify({'sucesso': False, 'mensagem': 'Não há números disponíveis'}), 400

    numeros_novos = [int(numero) for numero in numeros_sorte.split(',') if numero]

    if participante.status == 'pendente':
        participante.status = 'aprovado'
        participante.numeros_sorte = formatar_numeros(numeros_novos)
        atualizar_status_lote_historico(participante, participante.lote_cadastro, 'aprovado')
        assunto_email = 'Sua rifa foi aprovada!'
        titulo_email = 'Bem-vindo à Rifa!'
        descricao_email = 'Seu cadastro foi aprovado com sucesso!'
        mensagem_retorno = 'Participante aprovado com sucesso'
    else:
        numeros_totais = obter_numeros_lista(participante) + numeros_novos
        participante.quantidade_tickets += quantidade_aprovada
        participante.numeros_sorte = formatar_numeros(numeros_totais)
        atualizar_status_lote_historico(participante, participante.lote_pendente, 'aprovado')
        participante.quantidade_tickets_pendente = None
        participante.comprovante_pendente = None
        participante.comprovantes_pendente = None
        participante.data_solicitacao_extra = None
        participante.motivo_rejeicao_pendente = None
        participante.lote_pendente = None
        assunto_email = 'Sua compra adicional foi aprovada!'
        titulo_email = 'Compra adicional aprovada!'
        descricao_email = 'Seu novo comprovante foi aprovado e os números adicionais já foram liberados.'
        mensagem_retorno = 'Compra adicional aprovada com sucesso'

    participante.data_aprovacao = datetime.utcnow()
    db.session.commit()
    
    numeros_lista = ', '.join(map(str, numeros_novos))
    numeros_totais_lista = ', '.join(map(str, obter_numeros_lista(participante)))
    corpo_email = f"""
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f6f8fb; padding: 24px; color: #243447;">
            <div style="max-width: 640px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 30px rgba(36, 52, 71, 0.12);">
                <div style="padding: 32px; text-align: center; background: linear-gradient(135deg, #1f6feb, #2ea043); color: #ffffff;">
                    <img src="cid:pingo-photo" alt="Pingo" style="width: 180px; height: 180px; object-fit: cover; border-radius: 50%; border: 4px solid rgba(255,255,255,0.9); margin-bottom: 16px;">
                    <h2 style="margin: 0;">{titulo_email}</h2>
                </div>
                <div style="padding: 32px;">
                    <p>{descricao_email}</p>
                    <p style="font-size: 18px; font-weight: bold; color: #2ea043;">Muito Obrigado! O pingo agradece a sua contribuição!</p>
                    <p><strong>Novos números da sorte:</strong></p>
                    <h3 style="color: #1f6feb;">{numeros_lista}</h3>
                    <p><strong>Todos os seus números da sorte:</strong></p>
                    <p style="font-size: 16px; line-height: 1.8;">{numeros_totais_lista}</p>
                    <p>Boa sorte!</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    email_enviado, erro_email = enviar_email(participante.email, assunto_email, corpo_email)

    if email_enviado:
        return jsonify({
            'sucesso': True,
            'mensagem': f'{mensagem_retorno} e email enviado.'
        })

    return jsonify({
        'sucesso': False,
        'aprovado': True,
        'mensagem': f'{mensagem_retorno}, mas o email falhou: {erro_email}'
    }), 502

@app.route('/api/admin/rejeitar/<int:participante_id>', methods=['POST'])
@login_required
def rejeitar_participante(participante_id):
    data = request.get_json()
    motivo = data.get('motivo', 'Não especificado')
    
    participante = Participante.query.get_or_404(participante_id)
    
    rejeicao_adicional = possui_solicitacao_extra_pendente(participante) and participante.status == 'aprovado'

    if participante.status == 'pendente':
        participante.status = 'rejeitado'
        participante.motivo_rejeicao = motivo
        atualizar_status_lote_historico(participante, participante.lote_cadastro, 'rejeitado')
        assunto_email = 'Seu cadastro foi rejeitado'
        titulo_email = 'Rifa - Cadastro Rejeitado'
        mensagem_retorno = 'Participante rejeitado'
        texto_email = 'Seu cadastro foi rejeitado.'
    elif rejeicao_adicional:
        atualizar_status_lote_historico(participante, participante.lote_pendente, 'rejeitado')
        participante.quantidade_tickets_pendente = None
        participante.comprovante_pendente = None
        participante.comprovantes_pendente = None
        participante.data_solicitacao_extra = None
        participante.motivo_rejeicao_pendente = motivo
        participante.lote_pendente = None
        assunto_email = 'Sua compra adicional foi rejeitada'
        titulo_email = 'Rifa - Compra adicional rejeitada'
        mensagem_retorno = 'Compra adicional rejeitada'
        texto_email = 'Sua solicitação de números adicionais foi rejeitada.'
    else:
        return jsonify({'sucesso': False, 'mensagem': 'Participante não está pendente'}), 400

    db.session.commit()
    
    corpo_email = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>{titulo_email}</h2>
            <p>{texto_email}</p>
            <p><strong>Motivo:</strong> {motivo}</p>
            <p>Se tiver dúvidas, entre em contato conosco.</p>
        </body>
    </html>
    """
    
    email_enviado, erro_email = enviar_email(participante.email, assunto_email, corpo_email)

    if email_enviado:
        return jsonify({
            'sucesso': True,
            'mensagem': f'{mensagem_retorno} e email enviado.'
        })

    return jsonify({
        'sucesso': False,
        'rejeitado': True,
        'mensagem': f'{mensagem_retorno}, mas o email falhou: {erro_email}'
    }), 502

@app.route('/api/admin/comprovante/<int:participante_id>')
@login_required
def visualizar_comprovante(participante_id):
    participante = Participante.query.get_or_404(participante_id)
    tipo_solicitacao = request.args.get('tipo', 'cadastro_inicial')
    comprovante = participante.comprovante_pendente if tipo_solicitacao == 'compra_adicional' else participante.comprovante
    return redirect(f"/static/uploads/{comprovante}")

@app.route('/api/admin/comprovante/<int:participante_id>/<path:filename>')
@login_required
def visualizar_comprovante_arquivo(participante_id, filename):
    participante = Participante.query.get_or_404(participante_id)
    arquivos_permitidos = {
        item.get('arquivo')
        for item in obter_historico_comprovantes(participante)
        if item.get('arquivo')
    }

    arquivos_permitidos.update(obter_comprovantes_campo(participante, 'comprovantes', 'comprovante'))
    arquivos_permitidos.update(obter_comprovantes_campo(participante, 'comprovantes_pendente', 'comprovante_pendente'))

    if filename not in arquivos_permitidos:
        return jsonify({'sucesso': False, 'mensagem': 'Comprovante não encontrado para este participante.'}), 404

    return redirect(f"/static/uploads/{filename}")

if __name__ == '__main__':
    app.run(debug=DEBUG_MODE, host='0.0.0.0', port=APP_PORT)
