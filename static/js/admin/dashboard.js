let clienteSelecionadoId = null;
let modalSaldo = null;

document.addEventListener('DOMContentLoaded', function() {
    // Inicializar modal
    const modalElement = document.getElementById('modalSaldo');
    if (modalElement) {
        modalSaldo = new bootstrap.Modal(modalElement);
    }
});

// Inicializar DataTable quando o jQuery estiver pronto
window.addEventListener('load', function() {
    if (typeof $ !== 'undefined' && typeof $.fn.DataTable !== 'undefined') {
        $('#tabelaUsuarios').DataTable({
            language: {
                url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/pt-BR.json'
            },
            order: [[0, 'asc']],
            responsive: true
        });
    }
});

function abrirModalSaldo(usuarioId, nome) {
    if (!modalSaldo) return;
    
    clienteSelecionadoId = usuarioId;
    document.getElementById('nomeCliente').textContent = nome;
    document.getElementById('valor').value = '';
    modalSaldo.show();
}

function adicionarSaldo() {
    const valor = document.getElementById('valor').value;
    if (!valor || valor <= 0) {
        alert('Por favor, insira um valor válido.');
        return;
    }

    console.log(clienteSelecionadoId); // Verifica se o ID do cliente está correto
    fetch(`/admin/adicionar_saldo/${clienteSelecionadoId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ valor: parseFloat(valor) })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            modalSaldo.hide(); 
            window.location.reload(); 
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        alert('Erro ao adicionar saldo.');
    });
}

function editarUsuario(id) {
    window.location.href = `/editar_usuario/${id}`;
}

function alterarStatus(id, ativar) {
    const url = ativar ? `/ativar_usuario/${id}` : `/desativar_usuario/${id}`;
    fetch(url, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.reload();
            } else {
                alert(data.message || 'Erro ao alterar status do usuário.');
            }
        })
        .catch(error => {
            console.error('Erro:', error);
            alert('Erro ao alterar status do usuário.');
        });
}
