// Funções de Transferência
function realizarTransferencia(event) {
    event.preventDefault();
    const form = event.target;
    const data = {
        conta_destino: form.querySelector('[name="conta_destino"]').value,
        valor: parseFloat(form.querySelector('[name="valor"]').value),
        descricao: form.querySelector('[name="descricao"]').value
    };

    fetch('/transferencia', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            mostrarAlerta('error', data.error);
        } else {
            mostrarAlerta('success', 'Transferência realizada com sucesso!');
            setTimeout(() => window.location.reload(), 2000);
        }
    })
    .catch(error => {
        mostrarAlerta('error', 'Erro ao realizar transferência. Tente novamente.');
    });
}

// Funções de Alerta
function mostrarAlerta(tipo, mensagem) {
    const alertaDiv = document.createElement('div');
    alertaDiv.className = `alert alert-${tipo === 'error' ? 'danger' : 'success'} alert-dismissible fade show`;
    alertaDiv.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.querySelector('.container-fluid').insertAdjacentElement('afterbegin', alertaDiv);
    
    setTimeout(() => {
        alertaDiv.remove();
    }, 5000);
}

// Funções de Formatação
function formatarMoeda(valor) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(valor);
}

function formatarData(data) {
    return new Intl.DateTimeFormat('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(new Date(data));
}

// Funções de Máscara
function mascaraCPF(input) {
    let valor = input.value.replace(/\D/g, '');
    valor = valor.replace(/(\d{3})(\d)/, '$1.$2');
    valor = valor.replace(/(\d{3})(\d)/, '$1.$2');
    valor = valor.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    input.value = valor;
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Inicializa os tooltips do Bootstrap
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => new bootstrap.Tooltip(tooltip));

    // Adiciona máscaras aos campos
    const cpfInputs = document.querySelectorAll('input[name="cpf"]');
    cpfInputs.forEach(input => {
        input.addEventListener('input', () => mascaraCPF(input));
    });

    // Adiciona listeners aos formulários de transferência
    const formTransferencia = document.querySelector('#formTransferencia');
    if (formTransferencia) {
        formTransferencia.addEventListener('submit', realizarTransferencia);
    }

    // Formata valores monetários
    document.querySelectorAll('.valor-moeda').forEach(elemento => {
        const valor = parseFloat(elemento.textContent);
        elemento.textContent = formatarMoeda(valor);
    });

    // Formata datas
    document.querySelectorAll('.data-formatada').forEach(elemento => {
        elemento.textContent = formatarData(elemento.textContent);
    });
});

// Funções para os gráficos
function atualizarGraficos() {
    // Atualiza os gráficos com dados do servidor
    fetch('/api/dados_graficos')
        .then(response => response.json())
        .then(data => {
            if (window.movimentacaoChart) {
                window.movimentacaoChart.data = data.movimentacao;
                window.movimentacaoChart.update();
            }
            if (window.gastosChart) {
                window.gastosChart.data = data.gastos;
                window.gastosChart.update();
            }
        })
        .catch(error => console.error('Erro ao atualizar gráficos:', error));
}

// Atualiza os gráficos a cada 5 minutos
setInterval(atualizarGraficos, 300000);
