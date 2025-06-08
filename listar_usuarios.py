from app import app, Usuario, db

with app.app_context():
    usuarios = Usuario.query.all()
    print("\n=== Usuários Cadastrados ===")
    print("ID | Nome | Email | Tipo | Saldo | Ativo")
    print("-" * 70)
    for usuario in usuarios:
        print(f"{usuario.id} | {usuario.nome} | {usuario.email} | {usuario.tipo} | R${usuario.saldo:.2f} | {'Sim' if usuario.ativo else 'Não'}")
    print("-" * 70)
    print(f"Total de usuários: {len(usuarios)}\n")
