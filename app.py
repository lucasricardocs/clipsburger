from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime
import plotly.graph_objs as go
import plotly.io as pio

app = Flask(__name__)

# Cria o banco de dados e a tabela se não existirem
def criar_tabela():
    conn = sqlite3.connect('vendas.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            dinheiro REAL DEFAULT 0,
            cartao REAL DEFAULT 0,
            pix REAL DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

criar_tabela()

# Rota principal
@app.route('/', methods=['GET', 'POST'])
def index():
    conn = sqlite3.connect('vendas.db')
    if request.method == 'POST':
        data = request.form['data']
        dinheiro = float(request.form.get('dinheiro', 0))
        cartao = float(request.form.get('cartao', 0))
        pix = float(request.form.get('pix', 0))

        conn.execute('INSERT INTO vendas (data, dinheiro, cartao, pix) VALUES (?, ?, ?, ?)', (data, dinheiro, cartao, pix))
        conn.commit()
        return redirect('/')

    # Filtro de mês e ano
    mes = request.args.get('mes')
    ano = request.args.get('ano')

    query = 'SELECT * FROM vendas'
    params = []

    if mes and ano:
        query += ' WHERE strftime("%m", data) = ? AND strftime("%Y", data) = ?'
        params.extend([mes.zfill(2), ano])

    query += ' ORDER BY data ASC'
    vendas = conn.execute(query, params).fetchall()

    # Gerar gráfico de acumulação
    datas = []
    valores_acumulados = []
    acumulado = 0
    for venda in vendas:
        data = venda[1]
        valor = venda[2] + venda[3] + venda[4]
        acumulado += valor
        datas.append(data)
        valores_acumulados.append(acumulado)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=datas, y=valores_acumulados, mode='lines+markers', name='Acumulado'))
    fig.update_layout(title='Acumulação de Vendas', xaxis_title='Data', yaxis_title='Valor Acumulado')

    grafico = pio.to_html(fig, full_html=False)

    # Buscar todos os meses e anos para o filtro
    meses_anos = conn.execute('SELECT DISTINCT strftime("%m", data), strftime("%Y", data) FROM vendas').fetchall()

    conn.close()

    return render_template('index.html', vendas=vendas, grafico=grafico, meses_anos=meses_anos, mes_selecionado=mes, ano_selecionado=ano)

if __name__ == '__main__':
    app.run(debug=True)
