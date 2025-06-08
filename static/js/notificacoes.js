function carregarNotificacoes() {
    fetch('/notificacoes/nao-lidas')
        .then(response => response.json())
        .then(notificacoes => {
            const badge = document.getElementById('notificacoesBadge');
            const list = document.getElementById('notificacoesList');
            
            // Atualizar contador
            if (notificacoes.length > 0) {
                badge.textContent = notificacoes.length;
                badge.classList.remove('d-none');
            } else {
                badge.classList.add('d-none');
            }
            
            // Limpar lista atual
            list.innerHTML = '';
            
            // Adicionar notificações
            notificacoes.forEach(n => {
                const item = document.createElement('div');
                item.className = 'list-group-item list-group-item-action';
                
                let icon = '';
                switch (n.tipo) {
                    case 'info':
                        icon = '<i class="bx bx-info-circle text-info"></i>';
                        break;
                    case 'success':
                        icon = '<i class="bx bx-check-circle text-success"></i>';
                        break;
                    case 'warning':
                        icon = '<i class="bx bx-error text-warning"></i>';
                        break;
                    case 'danger':
                        icon = '<i class="bx bx-x-circle text-danger"></i>';
                        break;
                }
                
                item.innerHTML = `
                    <div class="d-flex w-100 justify-content-between align-items-center">
                        <h6 class="mb-1">${icon} ${n.titulo}</h6>
                        <small>${n.data}</small>
                    </div>
                    <p class="mb-1">${n.mensagem}</p>
                    ${n.link ? `<a href="${n.link}" class="btn btn-sm btn-primary mt-2">Ver mais</a>` : ''}
                `;
                
                // Marcar como lida ao clicar
                item.addEventListener('click', () => {
                    fetch(`/notificacoes/${n.id}/marcar-como-lida`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    }).then(() => {
                        carregarNotificacoes();
                    });
                });
                
                list.appendChild(item);
            });
            
            if (notificacoes.length === 0) {
                const emptyMessage = document.createElement('div');
                emptyMessage.className = 'list-group-item text-center text-muted';
                emptyMessage.textContent = 'Nenhuma notificação não lida';
                list.appendChild(emptyMessage);
            }
        });
}

// Carregar notificações ao iniciar
document.addEventListener('DOMContentLoaded', () => {
    carregarNotificacoes();
    
    // Atualizar a cada 30 segundos
    setInterval(carregarNotificacoes, 30000);
});
