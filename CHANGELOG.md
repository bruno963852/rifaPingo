# MUDANÇAS REALIZADAS - Versão 2

## 🔐 Autenticação

### Admin
- ✅ Página `/admin/login` adicionada com proteção por senha
- ✅ Logout em `/admin/logout`
- ✅ Decorador `@login_required` para proteger rotas admin
- ✅ Senha configurada via `.env` (ADMIN_PASSWORD)
- ✅ Sessões Flask para manter usuário autenticado

## 👤 Cadastro de Participantes

### Removido
- ❌ Campo de telefone

### Adicionado
- ✅ Campo de senha (mínimo 6 caracteres)
- ✅ Permissão para usuários rejeitados refazerem cadastro
- ✅ Exclusão automática de cadastro anterior ao reprocessar

### Modelo de Dados
```python
# Antes
email (UNIQUE)
telefone
quantidade_tickets
comprovante
status
...

# Depois
email (não unique - permite reprocessamento)
senha
quantidade_tickets
comprovante
status
...
```

## 🔍 Página de Consulta

### Antes
- Email OU Telefone

### Depois
- Email + Senha (autenticação necessária)
- Retorna status do cadastro
- Se rejeitado, oferece botão para refazer cadastro
- Mostra números da sorte apenas se aprovado

## 🛡️ Painel Administrativo

### Proteção
- ✅ Requer login com senha
- ✅ Redireciona para `/admin/login` se não autenticado
- ✅ Botão de logout na navbar

### Interface
- ✅ Removida coluna de telefone
- ✅ Mantém todas as funcionalidades de aprovação/rejeição
- ✅ Auto-atualiza a cada 3 segundos

## 📧 Emails

### Sem mudanças
- Aprovação: Números da sorte enviados
- Rejeição: Motivo da rejeição enviado
- Reprocessamento: Usuário pode criar novo cadastro

## 🗄️ Banco de Dados

### Alterações de Schema
1. Removido: Coluna `telefone`
2. Adicionado: Coluna `senha` (VARCHAR 255)
3. Email não é mais UNIQUE (permite reprocessamento)

### Para Atualizar
Se você tinha um banco de dados antigo:
```bash
rm rifa.db
python3 app.py
```

## 📝 Variáveis de Ambiente

### Adicionadas
```
ADMIN_PASSWORD=senha123
SECRET_KEY=rifa-key-2024-seguro
```

## 🔄 Fluxo de Reprocessamento

1. Usuário faz cadastro inicial → Status: pendente
2. Admin rejeita → Status: rejeitado
3. Usuário acessa `/consultar` com email e senha
4. Sistema mostra motivo da rejeição + botão "Fazer novo cadastro"
5. Usuário clica no botão → Vai para `/cadastro`
6. Sistema deleta cadastro rejeitado anterior
7. Novo cadastro é criado → Volta para status: pendente
8. Processo se repete

## 🚀 Como Testar

### 1. Fazer Cadastro
```
GET /cadastro
POST /cadastro
  - email: test@example.com
  - senha: 123456
  - quantidade_tickets: 5
  - comprovante: (file)
```

### 2. Login Admin
```
GET /admin/login
POST /admin/login
  - senha: senha123 (ou o que você configurou em .env)
```

### 3. Consultar Números (Rejeitado)
```
POST /consultar
  - email: test@example.com
  - senha: 123456
  → Mostra motivo + botão para refazer
```

## ⚠️ Notas Importantes

1. **Senhas em texto plano**: Para produção, use bcrypt/werkzeug.security
2. **Email obrigatório**: Agora é o único identificador
3. **Reprocessamento direto**: Usuário pode imediatamente refazer após rejeição
4. **Session timeout**: Configure tempo de expiração de sessão para admin em produção

## 🔧 Próximos Passos (Recomendados)

1. Implementar hash de senha com bcrypt
2. Adicionar 2FA para admin
3. Adicionar rate limiting para login
4. Implementar auto-logout após inatividade
5. Adicionar logs de auditoria
6. Email como primary key (remover ID)
7. Implementar soft delete para dados históricos
