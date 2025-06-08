// Configuração padrão do DataTables em português
const dataTablesConfig = {
    responsive: true,
    language: {
        emptyTable: "Nenhum registro encontrado",
        info: "Mostrando _START_ até _END_ de _TOTAL_ registros",
        infoEmpty: "Mostrando 0 até 0 de 0 registros",
        infoFiltered: "(Filtrados de _MAX_ registros)",
        infoThousands: ".",
        loadingRecords: "Carregando...",
        processing: "Processando...",
        zeroRecords: "Nenhum registro encontrado",
        search: "Pesquisar",
        paginate: {
            next: "Próximo",
            previous: "Anterior",
            first: "Primeiro",
            last: "Último"
        },
        aria: {
            sortAscending: ": Ordenar colunas de forma ascendente",
            sortDescending: ": Ordenar colunas de forma descendente"
        },
        select: {
            rows: {
                "_": "Selecionado %d linhas",
                "0": "Nenhuma linha selecionada",
                "1": "Selecionado 1 linha"
            }
        },
        buttons: {
            copy: "Copiar",
            copyTitle: "Cópia bem sucedida",
            copySuccess: {
                "1": "Uma linha copiada com sucesso",
                "_": "%d linhas copiadas com sucesso"
            }
        }
    }
};
