from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)

# Função para conectar no banco
def get_db_connection():
    conn = sqlite3.connect('vendas.db')
    conn.row_factory = sqlite3.Row
    return conn

# Cria a tabela se não existir
def create_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            valor REAL NOT NULL,
            tipo_pagamento TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Rota principal
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        data = request.form['data']
        valor = float(request.form['valor'])
        tipo_pagamento = request.form['tipo_pagamento']
        
        conn = get_db_connection()
        conn.execute('INSERT INTO vendas (data, valor, tipo_pagamento) VALUES (?, ?, ?)',
                     (data, valor, tipo_pagamento))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    
    # Pega mês e ano do filtro
    mes = request.args.get('mes')
    ano = request.args.get('ano')

    conn = get_db_connection()
    if mes and ano:
        vendas = conn.execute('SELECT * FROM vendas WHERE strftime("%m", data) = ? AND strftime("%Y", data) = ? ORDER BY data ASC', (mes.zfill(2), ano)).fetchall()
    else:
        vendas = conn.execute('SELECT * FROM vendas ORDER BY data ASC').fetchall()
    conn.close()

    # Preparar dados para o gráfico
    acumulado = []
    total = 0
    datas = []
    for venda in vendas:
        total += venda['valor']
        datas.append(venda['data'])
        acumulado.append(total)

    return render_template('index.html', vendas=vendas, datas=datas, acumulado=acumulado)

# Inicializa
if __name__ == '__main__':
    create_table()
    app.run(debug=True)