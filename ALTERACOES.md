# ✅ RESUMO DAS ALTERAÇÕES

## O que foi pedido

1. ✅ Remover telefone do cadastro
2. ✅ Pedir somente email e senha
3. ✅ Para consultar números: fornecer email e senha
4. ✅ Se rejeitado: possibilidade de retificar dados e refazer upload
5. ✅ Página /admin protegida por senha hardcoded do .env

---

## O que foi implementado

### 1️⃣ Cadastro (Novo)
**Rota**: `GET/POST /cadastro`

**Formulário agora pede:**
- ✅ Email (validado)
- ✅ Senha (mínimo 6 caracteres)
- ✅ Quantidade de tickets (1-100)
- ✅ Comprovante de pagamento PIX (arquivo)

**Removido:**
- ❌ Campo de telefone

**Lógica de reprocessamento:**
- Se email existe e status = 'rejeitado' → deleta cadastro anterior
- Se email existe e status ≠ 'rejeitado' → erro (já cadastrado)
- Novo cadastro criado com status 'pendente'

---

### 2️⃣ Consulta (Novo)
**Rota**: `GET/POST /consultar`

**Formulário agora pede:**
- ✅ Email (validado)
- ✅ Senha (verificada)

**Fluxo de respostas:**
1. Email ou senha vazios → Erro
2. Email não encontrado → Erro
3. Senha incorreta → Erro
4. Status = 'pendente' → Aguardando aprovação
5. Status = 'rejeitado' → Motivo + Botão "Fazer novo cadastro"
6. Status = 'aprovado' → Números da sorte exibidos

**Removido:**
- ❌ Opção de buscar por telefone
- ❌ Campo de telefone na resposta

---

### 3️⃣ Admin (Protegido)
**Rota**: `GET/POST /admin/login`

**Login**:
- ✅ Senha solicitada (hardcoded do `.env`)
- ✅ ADMIN_PASSWORD configurável
- ✅ Sessão Flask mantém autenticação
- ✅ Decorador @login_required protege rotas

**URLs protegidas**:
- `/admin` → Painel administrativo
- `/api/admin/participantes` → Listagem
- `/api/admin/aprovar/<id>` → Aprovação
- `/api/admin/rejeitar/<id>` → Rejeição
- `/api/admin/comprovante/<id>` → Visualizar arquivo
- `/admin/logout` → Sair

**Navbar do admin**:
- ✅ Link "Sair" em vermelho

**Tabela removida coluna**:
- ❌ Telefone

---

## Modelo de Dados (Banco de Dados)

### Antes
```python
email (UNIQUE=True)      # Impedia reprocessamento
telefone (String 20)
quantidade_tickets
comprovante
status
data_criacao
data_aprovacao
numeros_sorte
motivo_rejeicao
```

### Depois
```python
email (UNIQUE=False)     # Permite deletar e refazer
senha (String 255)       # NOVA
telefone (REMOVIDO)
quantidade_tickets
comprovante
status
data_criacao
data_aprovacao
numeros_sorte
motivo_rejeicao
```

---

## Variáveis de Ambiente (.env)

### Novas
```dotenv
ADMIN_PASSWORD=senha123          # Senha do admin
SECRET_KEY=rifa-key-2024-seguro  # Chave de sessão
```

---

## Templates Alterados

### ✅ cadastro.html
- ❌ Removido campo telefone
- ✅ Adicionado campo senha
- ✅ Validação de senha mínimo 6 caracteres

### ✅ consultar.html
- ❌ Removido campo telefone (agora input único para email)
- ✅ Adicionado campo senha
- ✅ Input group removido (já não é OU)
- ✅ Botão "Fazer novo cadastro" se rejeitado
- ❌ Removido telefone da resposta de aprovado

### ✅ admin.html
- ✅ Botão "Sair" na navbar
- ❌ Removida coluna telefone da tabela

### ✨ admin_login.html (NOVO)
- ✅ Página de login protegida
- ✅ Input de senha
- ✅ Mensagem de erro se senha incorreta

---

## Rotas Novas

```
GET  /admin/login           → Formulário de login
POST /admin/login           → Verificar senha
GET  /admin/logout          → Sair da sessão
```

---

## Fluxos Atualizados

### Fluxo de Cadastro
```
Usuário preenche:
  - Email
  - Senha
  - Quantidade de tickets
  - Comprovante

Se email já existe e status = 'pendente'/''aprrovado':
  → Erro: "Este email já foi cadastrado"

Se email já existe e status = 'rejeitado':
  → Deleta cadastro anterior
  → Cria novo cadastro
  → Vai para fila novamente

Status padrão: 'pendente'
```

### Fluxo de Consulta
```
Usuário fornece:
  - Email
  - Senha (não pode ser vazio)

Validações:
  1. Email + Senha preenchidos?
  2. Email existe no banco?
  3. Senha está correta?
  4. Qual é o status?

Se rejeitado:
  → Mostra motivo
  → Oferta botão "Fazer novo cadastro"
  → Redireciona para /cadastro
```

### Fluxo de Admin
```
Admin acessa:
  1. POST /admin/login com senha
  2. Se correto → session['admin_logged'] = True
  3. Acessa /admin (protegido)
  4. Coloca @login_required em rotas
  5. Se não autenticado → redireciona para /admin/login
  6. Clica logout → remove session
```

---

## Dados de Exemplo

### Cadastro
```json
{
  "email": "usuario@example.com",
  "senha": "123456",
  "quantidade_tickets": 3,
  "comprovante": "<arquivo>"
}
```

### Consulta
```json
{
  "email": "usuario@example.com",
  "senha": "123456"
}
```

### Login Admin
```json
{
  "senha": "senha123"
}
```

---

## Testes Recomendados

1. **Cadastro** → Email + senha → Deve funcionar
2. **Consulta pendente** → Email + senha → Aguardando
3. **Admin login** → Senha correta → Acesso
4. **Admin login** → Senha incorreta → Erro
5. **Reprocessamento** → Rejeitar → Novo cadastro → Volta para pendente
6. **Logout** → Sair → Redireciona

---

## Notas Importantes

⚠️ **Senhas em texto plano**
- A versão atual armazena senha SEM hash
- Para produção: usar bcrypt/werkzeug.security.generate_password_hash()

⚠️ **Email não é mais único**
- Permite reprocessamento
- Garanta que usuários rejeitados limpem dados antigos

⚠️ **Banco de dados antigo**
- Se você tinha um `rifa.db` antigo
- Faça backup e delete:
  ```bash
  cd /var/home/brunomartins/Projetos/python/rifa
  rm rifa.db
  python3 app.py
  ```

---

## Próximos Passos Sugeridos

1. Implementar hash de senha (bcrypt)
2. Adicionar 2FA para admin
3. Validar força da senha no cadastro
4. Implementar rate limiting
5. Adicionar logs de auditoria
6. Usar email como primary key
7. Implementar soft delete
8. Adicionar CSRF protection

---

**Status**: ✅ Todas as alterações implementadas e testadas
**Data**: 09/03/2026
**Versão**: 2.0
