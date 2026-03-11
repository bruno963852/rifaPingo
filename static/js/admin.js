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

    // Modal close
    const modal = document.getElementById('rejeicaoModal');
    const closeBtn = document.querySelector('.close');
    closeBtn.addEventListener('click', () => {
        modal.classList.remove('show');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
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
                tableBody.innerHTML = '<tr><td colspan="7" style="text-align: center;">Nenhum participante encontrado</td></tr>';
                return;
            }

            tableBody.innerHTML = data.map(p => `
                <tr>
                    <td>${p.email}</td>
                    <td>${p.quantidade_tickets}</td>
                    <td>${p.data_criacao}</td>
                    <td>
                        <a href="/api/admin/comprovante/${p.id}" target="_blank" class="btn-view">
                            Ver
                        </a>
                    </td>
                    <td>${p.numeros_sorte || '-'}</td>
                    <td>
                        <div class="table-actions">
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
            document.getElementById('tableBody').innerHTML = '<tr><td colspan="7" style="text-align: center; color: red;">Erro ao carregar dados</td></tr>';
        });
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
        } else {
            alert('Erro: ' + data.mensagem);
        }
    })
    .catch(error => {
        alert('Erro ao rejeitar participante: ' + error.message);
    });
}
