import sqlite3
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    try:
        # Conecta ao banco de dados (verifique se o caminho está correto)
        conn = sqlite3.connect('vendas.db')
        
        # Tenta buscar as vendas
        vendas = conn.execute('SELECT * FROM vendas ORDER BY data ASC').fetchall()
        
        # Fecha a conexão
        conn.close()

        return render_template('index.html', vendas=vendas)

    except sqlite3.Error as e:
        # Se houver erro, captura e imprime
        return f"Erro no banco de dados: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
