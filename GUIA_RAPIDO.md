# GUIA RÁPIDO - Rifa 100

## 🚀 Iniciando Rápido

### 1. Instalar Dependências
```bash
cd /var/home/brunomartins/Projetos/python/rifa
pip3 install -r requirements.txt
```

### 2. Configurar Email
Edite o arquivo `.env` com suas credenciais:
```bash
nano .env
```

**Configuração Gmail:**
1. Ative autenticação de 2 fatores em myaccount.google.com
2. Gere uma "Senha de App" em: https://myaccount.google.com/apppasswords
3. Copie a senha gerada para o arquivo `.env`

### 3. Iniciar Aplicação
```bash
python3 app.py
```

Acesse: **http://localhost:5000**

---

## 📋 Páginas Disponíveis

| URL | Descrição |
|-----|-----------|
| `/` | Página inicial com estatísticas em tempo real |
| `/cadastro` | Formulário para participantes se cadastrarem |
| `/consultar` | Buscar números da sorte por email ou telefone |
| `/admin` | Painel administrativo para gerenciar cadastros |

---

## 👥 Como Usar - Participante

1. **Acesse http://localhost:5000**
2. **Clique em "Participar Agora"**
3. **Preencha o formulário:**
   - Email (obrigatório e único)
   - Telefone (com DDD)
   - Quantidade de tickets desejados
   - Comprovante de pagamento PIX (PDF, PNG, JPG)
4. **Aguarde aprovação** - você receberá um email com seus números
5. **Consulte seus números** em /consultar quando aprovado

---

## 🔧 Como Gerenciar - Administrador

1. **Acesse http://localhost:5000/admin**

### Painel com 3 abas:

#### 📋 Pendentes (padrão)
- Lista todos os cadastros aguardando aprovação
- Botão "Ver" para visualizar o comprovante
- Botões de ação: Aprovar / Rejeitar

#### ✅ Aprovados
- Histórico de todas as aprovações
- Mostra os números da sorte de cada participante
- Sem ações disponíveis

#### ❌ Rejeitados
- Histórico de rejeições
- Mostra o motivo de cada rejeição
- Sem ações disponíveis

### Fluxo de Aprovação:

1. **Verificar Comprovante**: Clique em "Ver" para abrir a imagem
2. **Aprovar**:
   - Clique em "Aprovar"
   - Sistema gera números sequenciais
   - Email é enviado automaticamente
3. **Rejeitar**:
   - Clique em "Rejeitar"
   - Digite o motivo (ex: "Comprovante expirado")
   - Clique em "Confirmar Rejeição"
   - Cadastro fica marcado como rejeitado
   - **Usuário pode refazer o cadastro**

---

## 📊 Estatísticas em Tempo Real

Na página inicial, você vê:
- **Cadastros Confirmados**: Aprovados e com números atribuídos
- **Em Espera**: Pendentes de aprovação
- **Total**: Soma dos dois anteriores
- **Status**: Sorteio aberto ou cheio (máximo 100)

Atualiza automaticamente a cada 3 segundos!

---

## 💾 Banco de Dados

**Arquivo**: `rifa.db` (SQLite)

Criado automaticamente na primeira execução com a tabela:

```sql
Participantes (
  id (PK),
  email,
  senha,
  quantidade_tickets,
  comprovante (filename),
  status (pendente/aprovado/rejeitado),
  data_criacao,
  data_aprovacao,
  numeros_sorte,
  motivo_rejeicao
)
```

---

## 📁 Uploads

Os comprovantes são salvos em: `/static/uploads/`

Nomeados como: `email_timestamp_filename`

---

## 🐛 Dicas de Troubleshooting

### Porta 5000 em uso?
```bash
python3 app.py --port 5001
```

### Limpar banco de dados?
```bash
rm rifa.db
# Reinicie a aplicação
```

### Ver logs detalhados?
Edite `app.py` e mude:
```python
app.run(debug=True)  # Já está assim por padrão
```

---

## 🔐 Novo: Autenticação

### Para Admin
- URL: **http://localhost:5000/admin**
- **Senha necessária** (configurada em `.env`)
- Padrão: `senha123` (mude para produção!)

### Para Participante (Consulta)
- URL: **http://localhost:5000/consultar**
- **Email + Senha necessários**
- A senha é definida no cadastro

---

## 👤 Novo: Cadastro Simplificado

**Campos agora:**
- ✅ Email
- ✅ Senha (mínimo 6 caracteres)
- ✅ Quantidade de tickets
- ✅ Comprovante PIX

**Removido:**
- ❌ Telefone

---

## ♻️ Novo: Reprocessamento de Cadastros

Se seu cadastro foi rejeitado:

1. **Consulte seus números** em `/consultar`
2. Digite email e senha
3. Sistema mostra motivo e oferece **"Fazer novo cadastro"**
4. Você pode **refazer e reenviar** os comprovantes
5. Volta à fila de espera

---

## 🛡️ Segurança

⚠️ **Importante:**
- Mude a senha admin em `.env` → `ADMIN_PASSWORD`
- Configure uma SECRET_KEY forte para produção
- Use senhas seguras

---

---

## ✉️ Emails Automáticos

### Aprovação:
- Para: Email do participante
- Assunto: "Sua rifa foi aprovada!"
- Conteúdo: Números da sorte

### Rejeição:
- Para: Email do participante
- Assunto: "Seu cadastro foi rejeitado"
- Conteúdo: Motivo da rejeição

---

## 📞 Contato/Suporte

Para dúvidas ou bugs, consulte:
- Documentação completa: [README.md](README.md)
- Código: [app.py](app.py)

---

**Boa sorte com sua rifa! 🎰**
