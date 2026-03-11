from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'rifa-key-2024-seguro')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rifa.db'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Criar pasta de uploads se não existir
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Configurações de email (alterar com suas credenciais)
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', 'seu_email@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'sua_senha')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))

# Configuração de admin
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'senha123')

# Extensões de arquivo permitidas
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    email = db.Column(db.String(120), nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    quantidade_tickets = db.Column(db.Integer, nullable=False)
    comprovante = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='pendente')  # pendente, aprovado, rejeitado
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_aprovacao = db.Column(db.DateTime)
    numeros_sorte = db.Column(db.String(500))  # string com números separados por vírgula
    motivo_rejeicao = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<Participante {self.email}>'

# Criar tabelas
with app.app_context():
    db.create_all()

# Função para enviar email
def enviar_email(destinatario, assunto, corpo_html):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = assunto
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = destinatario
        
        parte_html = MIMEText(corpo_html, 'html')
        msg.attach(parte_html)
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, destinatario, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False

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
    numeros_disponiveis = [n for n in range(1, 101) if n not in numeros_usados]
    
    # Se não houver números suficientes, retornar vazio
    if len(numeros_disponiveis) < quantidade:
        return None
    
    numeros_sorte = numeros_disponiveis[:quantidade]
    return ','.join(map(str, sorted(numeros_sorte)))

# Rotas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    confirmados = Participante.query.filter_by(status='aprovado').count()
    em_espera = Participante.query.filter_by(status='pendente').count()
    total_bloqueado = confirmados + em_espera
    bloqueado = True if total_bloqueado >= 100 else False
    
    return jsonify({
        'confirmados': confirmados,
        'em_espera': em_espera,
        'total': total_bloqueado,
        'bloqueado': bloqueado
    })

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        # Verificar se está bloqueado
        stats = get_stats().get_json()
        if stats['bloqueado']:
            return jsonify({'sucesso': False, 'mensagem': 'Sorteio está cheio! Não é possível fazer novos cadastros.'}), 400
        
        email = request.form.get('email', '').lower().strip()
        senha = request.form.get('senha', '').strip()
        quantidade_str = request.form.get('quantidade_tickets', '0')
        
        # Validações
        if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return jsonify({'sucesso': False, 'mensagem': 'Email inválido'}), 400
        
        if not senha or len(senha) < 6:
            return jsonify({'sucesso': False, 'mensagem': 'Senha deve ter no mínimo 6 caracteres'}), 400
        
        try:
            quantidade = int(quantidade_str)
            if quantidade < 1 or quantidade > 100:
                return jsonify({'sucesso': False, 'mensagem': 'Quantidade deve ser entre 1 e 100'}), 400
        except ValueError:
            return jsonify({'sucesso': False, 'mensagem': 'Quantidade inválida'}), 400
        
        # Verificar se email já existe e está ativo
        participante_existente = Participante.query.filter_by(email=email).first()
        if participante_existente and participante_existente.status != 'rejeitado':
            return jsonify({'sucesso': False, 'mensagem': 'Este email já foi cadastrado'}), 400
        
        # Se o cadastro anterior foi rejeitado, remover e criar novo
        if participante_existente and participante_existente.status == 'rejeitado':
            db.session.delete(participante_existente)
            db.session.commit()
        
        # Verificar arquivo
        if 'comprovante' not in request.files:
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo foi enviado'}), 400
        
        file = request.files['comprovante']
        if file.filename == '':
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo foi selecionado'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'sucesso': False, 'mensagem': 'Tipo de arquivo não permitido. Use: PDF, PNG, JPG, GIF, BMP'}), 400
        
        # Salvar arquivo
        filename = secure_filename(f"{email}_{datetime.now().timestamp()}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Criar participante
        participante = Participante(
            email=email,
            senha=senha,
            quantidade_tickets=quantidade,
            comprovante=filename,
            status='pendente'
        )
        db.session.add(participante)
        db.session.commit()
        
        return jsonify({'sucesso': True, 'mensagem': 'Cadastro realizado com sucesso! Aguarde a aprovação.'}), 201
    
    return render_template('cadastro.html')

@app.route('/consultar', methods=['GET', 'POST'])
def consultar():
    resultado = None
    
    if request.method == 'POST':
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
        elif participante.status == 'pendente':
            resultado = {'status': 'pendente', 'mensagem': 'Seu cadastro está aguardando aprovação'}
        elif participante.status == 'rejeitado':
            resultado = {
                'status': 'rejeitado', 
                'mensagem': f'Seu cadastro foi rejeitado. Motivo: {participante.motivo_rejeicao}',
                'email': participante.email
            }
        elif participante.status == 'aprovado':
            numeros = participante.numeros_sorte.split(',') if participante.numeros_sorte else []
            resultado = {
                'status': 'aprovado',
                'email': participante.email,
                'quantidade_tickets': participante.quantidade_tickets,
                'numeros_sorte': numeros,
                'data_aprovacao': participante.data_aprovacao.strftime('%d/%m/%Y %H:%M') if participante.data_aprovacao else ''
            }
    
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
    participantes = Participante.query.filter_by(status=status_filter).all()
    
    return jsonify([{
        'id': p.id,
        'email': p.email,
        'quantidade_tickets': p.quantidade_tickets,
        'comprovante': p.comprovante,
        'data_criacao': p.data_criacao.strftime('%d/%m/%Y %H:%M'),
        'numeros_sorte': p.numeros_sorte
    } for p in participantes])

@app.route('/api/admin/aprovar/<int:participante_id>', methods=['POST'])
@login_required
def aprovar_participante(participante_id):
    participante = Participante.query.get_or_404(participante_id)
    
    if participante.status != 'pendente':
        return jsonify({'sucesso': False, 'mensagem': 'Participante não está pendente'}), 400
    
    # Gerar números da sorte
    numeros_sorte = gerar_numeros_sorte(participante.quantidade_tickets)
    
    if not numeros_sorte:
        return jsonify({'sucesso': False, 'mensagem': 'Não há números disponíveis'}), 400
    
    participante.status = 'aprovado'
    participante.numeros_sorte = numeros_sorte
    participante.data_aprovacao = datetime.utcnow()
    db.session.commit()
    
    # Enviar email com números da sorte
    numeros_lista = ', '.join(numeros_sorte.split(','))
    corpo_email = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Bem-vindo à Rifa!</h2>
            <p>Seu cadastro foi aprovado com sucesso!</p>
            <p><strong>Seus números da sorte:</strong></p>
            <h3 style="color: #2ecc71;">{numeros_lista}</h3>
            <p>Boa sorte!</p>
        </body>
    </html>
    """
    
    enviar_email(participante.email, 'Sua rifa foi aprovada!', corpo_email)
    
    return jsonify({'sucesso': True, 'mensagem': 'Participante aprovado com sucesso!'})

@app.route('/api/admin/rejeitar/<int:participante_id>', methods=['POST'])
@login_required
def rejeitar_participante(participante_id):
    data = request.get_json()
    motivo = data.get('motivo', 'Não especificado')
    
    participante = Participante.query.get_or_404(participante_id)
    
    if participante.status != 'pendente':
        return jsonify({'sucesso': False, 'mensagem': 'Participante não está pendente'}), 400
    
    participante.status = 'rejeitado'
    participante.motivo_rejeicao = motivo
    db.session.commit()
    
    # Enviar email de rejeição
    corpo_email = f"""
    <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Rifa - Cadastro Rejeitado</h2>
            <p>Seu cadastro foi rejeitado.</p>
            <p><strong>Motivo:</strong> {motivo}</p>
            <p>Se tiver dúvidas, entre em contato conosco.</p>
        </body>
    </html>
    """
    
    enviar_email(participante.email, 'Seu cadastro foi rejeitado', corpo_email)
    
    return jsonify({'sucesso': True, 'mensagem': 'Participante rejeitado e removido do sistema.'})

@app.route('/api/admin/comprovante/<participante_id>')
@login_required
def visualizar_comprovante(participante_id):
    participante = Participante.query.get_or_404(participante_id)
    return redirect(f"/static/uploads/{participante.comprovante}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
