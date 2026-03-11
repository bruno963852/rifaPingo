# Rifa 100 - Sistema de Sorteio

Um sistema completo para gerenciar rifas online com validação de pagamento, geração de números da sorte e consultas em tempo real.

## Características

✨ **Funcionalidades principais:**
- Formulário de cadastro com **email e senha** (sem telefone)
- Upload de comprovante PIX para validação
- **Painel administrativo protegido por senha**
- Verificação manual de pagamentos e aprovação/rejeição
- Geração automática de números da sorte (seqüencial de 1 a 100)
- Envio de números por email após aprovação
- Página inicial com estatísticas em tempo real
- Bloqueio automático ao atingir 100 cadastros
- **Página de consulta protegida** com email + senha
- **Sistema de retificação**: usuários rejeitados podem refazer o cadastro e reenviar comprovantes
- Sistema de rejeição com notificação por email

## Requisitos

- Python 3.7+
- pip3

## Instalação

1. Clone ou copie o projeto para sua máquina:
```bash
cd /var/home/brunomartins/Projetos/python/rifa
```

2. Instale as dependências:
```bash
pip3 install -r requirements.txt
```

3. Configure as variáveis de ambiente:
```bash
cp .env.example .env
```

4. Abra o arquivo `.env` e preencha com suas credenciais de email:
```
EMAIL_ADDRESS=seu_email@gmail.com
EMAIL_PASSWORD=sua_senha_de_app
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### Configurando Email com Gmail

Se usar Gmail, você precisa:

1. Ativar a autenticação de dois fatores em sua conta Google
2. Gerar uma "Senha de App" em: https://myaccount.google.com/apppasswords
3. Usar essa senha no arquivo `.env` como EMAIL_PASSWORD

### Configurando Senha de Admin

No arquivo `.env`, configure uma senha forte para o painel administrativo:
```
ADMIN_PASSWORD=sua_senha_segura
``` 

## Uso

Inicie a aplicação:
```bash
python3 app.py
```

A aplicação estará disponível em: **http://localhost:5000**

### Acessando as páginas:

- **Página Inicial**: http://localhost:5000/
- **Formulário de Cadastro**: http://localhost:5000/cadastro
- **Consultar Números**: http://localhost:5000/consultar
- **Painel Admin**: http://localhost:5000/admin

## Fluxo de Uso

### Para Participantes:
1. Acessa a página inicial e vê as estatísticas
2. Clica em "Participar Agora"
3. Preenche o formulário (**email, senha, quantidade de tickets**)
4. Faz o pagamento via PIX
5. Envia o comprovante de pagamento
6. Aguarda a aprovação manual
7. **Recebe um email com seus números da sorte**
8. Pode consultar a qualquer momento usando **email e senha**
9. Se rejeitado, pode **refazer o cadastro e reenviar comprovantes**

### Para Administrador:
1. **Acessa http://localhost:5000/admin**
2. **Faz login com a senha configurada** em `.env` (ADMIN_PASSWORD)
3. Vê a lista de cadastros pendentes
4. Verifica o comprovante de pagamento
5. Aprova ou rejeita o cadastro
6. Se aprovado: números são gerados e enviados por email
7. Se rejeitado: cadastro é marcado para reprocessamento (usuário pode refazer)
8. Pode visualizar histórico de aprovados e rejeitados

## Estrutura do Projeto

```
rifa/
├── app.py                      # Aplicação Flask principal
├── requirements.txt            # Dependências Python
├── .env.example               # Exemplo de variáveis de ambiente
├── README.md                  # Este arquivo
├── templates/                 # Arquivos HTML
│   ├── index.html             # Página inicial
│   ├── cadastro.html          # Formulário de cadastro
│   ├── consultar.html         # Página de consulta
│   └── admin.html             # Painel administrativo
├── static/
│   ├── css/
│   │   └── style.css          # Estilos CSS
│   ├── js/
│   │   └── admin.js           # JavaScript do painel admin
│   └── uploads/               # Pasta para comprovantes (criada automaticamente)
└── rifa.db                    # Banco de (não há mais index de unicidade para permitir reprocessamento)
- **Senha**: Senha do participante (em texto plano nesta versão)

## Banco de Dados

O banco de dados SQLite é criado automaticamente na primeira execução. Armazena:

- **Email**: E-mail único do participante
- **Telefone**: Telefone de contato
- **Quantidade de tickets**: Números de tickets comprados
- **Comprovante**: Nome do arquivo enviado
- **Status**: pendente, aprovado ou rejeitado
- **Números da sorte**: Números gerados (separados por vírgula)
- **Data de criação**: Quando foi cadastrado
- ***Altere a senha de admin** no arquivo `.env` - não use "senha123"
2. **Implemente hash de senha** - atualmente as senhas são armazenadas em texto plano (use bcrypt/werkzeug.security)
3. Configure `debug=False` em `app.py`
4. Use um servidor de produção (gunicorn, waitress, etc.)
5. Configure HTTPS/SSL
6. Use um banco de dados mais robusto (PostgreSQL)
7. Implemente autenticação mais robusta no painel admin (2FA, etc)
8. Use sessions seguras com SECRET_KEY forte
9. Validação adicional de comprovantes (análise de imagem, detecção de fraude)
10
1. Configure `debug=False` em `app.py`
2. Use um servidor de produção (gunicorn, waitress, etc.)
3. Configure HTTPS/SSL
4. Use um banco de dados mais robusto (PostgreSQL)
5. Implemente autenticação no painel admin
6. Validação adicional de comprovantes
7. Use variáveis de ambiente seguras

## Personalizações Possíveis

- Alterar o limite de 100 cadastros
- Adicionar autenticação no painel admin
- Enviar notificações por SMS
- Integrar com sistema de pagamento real
- Adicionar relatórios em PDF
- Implementar sistema de backup automático
- Adicionar sorteio automático

## Solução de Problemas

### E-mails não estão sendo enviados?
- Verifique as credenciais no arquivo `.env`
- Confirme que ativou "Senhas de App" no Gmail
- Verifique se o servidor SMTP está correto

### Erro ao fazer upload de arquivo?
- Certifique-se que a pasta `static/uploads/` existe
- Verifique permissões de escrita na pasta
- Confirme que o arquivo não excede 16MB

### Página admin em branco?
- Verifique o console do navegador (F12) para erros JavaScript
- Verifique os logs da aplicação Flask

## Licença

Livre para uso pessoal e comercial.

## Suporte

Para dúvidas ou problemas, consulte a documentação do Flask ou entre em contato.

---

**Desenvolvido com ❤️ para facilitar rifas online**
