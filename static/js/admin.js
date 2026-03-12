let statusAtual = 'pendente';

document.addEventListener('DOMContentLoaded', () => {
    carregarParticipantes();
    
    // Event listeners para tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            statusAtual = e.target.dataset.status;
            carregarParticipantes();
        });
    });

    document.querySelectorAll('[data-close-modal]').forEach(btn => {
        btn.addEventListener('click', () => {
            fecharModal(btn.dataset.closeModal);
        });
    });

    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('show');
            }
        });
    });

    // Atualizar lista a cada 3 segundos
    setInterval(carregarParticipantes, 3000);
});

function carregarParticipantes() {
    fetch(`/api/admin/participantes?status=${statusAtual}`)
        .then(response => response.json())
        .then(data => {
            const tableBody = document.getElementById('tableBody');
            
            if (data.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">Nenhum participante encontrado</td></tr>';
                return;
            }

            tableBody.innerHTML = data.map(p => `
                <tr>
                    <td>${p.nome || '-'}</td>
                    <td>${p.email}</td>
                    <td>${p.tipo_label || '-'}</td>
                    <td>${p.quantidade_tickets}</td>
                    <td>${p.data_criacao}</td>
                    <td>
                        <a href="/api/admin/comprovante/${p.id}?tipo=${p.tipo_solicitacao || 'cadastro_inicial'}" target="_blank" class="btn-view">
                            Ver
                        </a>
                    </td>
                    <td>${p.numeros_sorte || '-'}</td>
                    <td>
                        <div class="table-actions">
                            <button
                                class="btn-edit"
                                data-id="${p.id}"
                                data-nome="${encodeURIComponent(p.nome || '')}"
                                data-quantidade="${p.quantidade_tickets}"
                                data-tipo="${p.tipo_solicitacao || 'cadastro_inicial'}"
                                data-pode-editar-quantidade="${p.pode_editar_quantidade ? 'true' : 'false'}"
                                onclick="abrirModalEdicaoFromButton(this)"
                            >
                                Editar
                            </button>
                            ${statusAtual === 'pendente' ? `
                                <button class="btn-approve" onclick="aprovarParticipante(${p.id})">
                                    Aprovar
                                </button>
                                <button class="btn-reject" onclick="abrirModalRejeicao(${p.id})">
                                    Rejeitar
                                </button>
                            ` : '-'}
                        </div>
                    </td>
                </tr>
            `).join('');
        })
        .catch(error => {
            console.error('Erro ao carregar participantes:', error);
            document.getElementById('tableBody').innerHTML = '<tr><td colspan="8" style="text-align: center; color: red;">Erro ao carregar dados</td></tr>';
        });
}

function fecharModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

function aprovarParticipante(id) {
    if (confirm('Tem certeza que deseja aprovar este participante?')) {
        fetch(`/api/admin/aprovar/${id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.sucesso) {
                alert(data.mensagem);
                carregarParticipantes();
            } else if (data.aprovado) {
                alert(data.mensagem);
                carregarParticipantes();
            } else {
                alert('Erro: ' + data.mensagem);
            }
        })
        .catch(error => {
            alert('Erro ao aprovar participante: ' + error.message);
        });
    }
}

function abrirModalRejeicao(id) {
    document.getElementById('participanteIdRejeitar').value = id;
    document.getElementById('motivo').value = '';
    document.getElementById('rejeicaoModal').classList.add('show');
}

function abrirModalEdicaoFromButton(button) {
    abrirModalEdicao(
        button.dataset.id,
        decodeURIComponent(button.dataset.nome || ''),
        Number(button.dataset.quantidade || 0),
        button.dataset.tipo || 'cadastro_inicial',
        button.dataset.podeEditarQuantidade === 'true'
    );
}

function abrirModalEdicao(id, nome, quantidade, tipoSolicitacao, podeEditarQuantidade) {
    document.getElementById('participanteIdEditar').value = id;
    document.getElementById('tipoSolicitacaoEditar').value = tipoSolicitacao;
    document.getElementById('podeEditarQuantidade').value = podeEditarQuantidade ? 'true' : 'false';
    document.getElementById('nomeEditar').value = nome || '';

    const grupoQuantidade = document.getElementById('grupoQuantidadeEditar');
    const quantidadeInput = document.getElementById('quantidadeEditar');
    const quantidadeHint = document.getElementById('quantidadeHint');

    if (podeEditarQuantidade) {
        grupoQuantidade.style.display = 'block';
        quantidadeInput.value = quantidade;
        quantidadeInput.required = true;
        quantidadeHint.textContent = tipoSolicitacao === 'compra_adicional'
            ? 'Ajuste a quantidade desta compra adicional antes de aprovar.'
            : 'Ajuste a quantidade do cadastro antes de aprovar.';
    } else {
        grupoQuantidade.style.display = 'none';
        quantidadeInput.value = '';
        quantidadeInput.required = false;
    }

    document.getElementById('edicaoModal').classList.add('show');
}

function salvarEdicao() {
    const id = document.getElementById('participanteIdEditar').value;
    const nome = document.getElementById('nomeEditar').value.trim();
    const tipoSolicitacao = document.getElementById('tipoSolicitacaoEditar').value;
    const podeEditarQuantidade = document.getElementById('podeEditarQuantidade').value === 'true';
    const payload = { nome, tipo_solicitacao: tipoSolicitacao };

    if (!nome) {
        alert('Por favor, informe o nome do participante.');
        return;
    }

    if (podeEditarQuantidade) {
        const quantidade = Number(document.getElementById('quantidadeEditar').value);
        if (!Number.isInteger(quantidade) || quantidade < 1 || quantidade > 200) {
            alert('A quantidade deve ser um número entre 1 e 200.');
            return;
        }
        payload.quantidade_tickets = quantidade;
    }

    fetch(`/api/admin/participantes/${id}`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            alert(data.mensagem);
            fecharModal('edicaoModal');
            carregarParticipantes();
        } else {
            alert('Erro: ' + data.mensagem);
        }
    })
    .catch(error => {
        alert('Erro ao salvar alterações: ' + error.message);
    });
}

function confirmarRejeicao() {
    const id = document.getElementById('participanteIdRejeitar').value;
    const motivo = document.getElementById('motivo').value;

    if (!motivo.trim()) {
        alert('Por favor, digite o motivo da rejeição');
        return;
    }

    fetch(`/api/admin/rejeitar/${id}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ motivo: motivo })
    })
    .then(response => response.json())
    .then(data => {
        if (data.sucesso) {
            alert(data.mensagem);
            document.getElementById('rejeicaoModal').classList.remove('show');
            carregarParticipantes();
        } else if (data.rejeitado) {
            alert(data.mensagem);
            document.getElementById('rejeicaoModal').classList.remove('show');
            carregarParticipantes();
        } else {
            alert('Erro: ' + data.mensagem);
        }
    })
    .catch(error => {
        alert('Erro ao rejeitar participante: ' + error.message);
    });
}
