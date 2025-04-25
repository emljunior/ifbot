from flask import Flask, render_template, request, jsonify
from flask_mail import Mail, Message
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer, ListTrainer
from werkzeug.utils import secure_filename
import os
import json
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Parâmetros para o Flask-Mail
app.config['MAIL_SERVER'] = ''
app.config['MAIL_PORT'] = 587                        
app.config['MAIL_USERNAME'] = '' 
app.config['MAIL_PASSWORD'] = ''     
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
mail = Mail(app)

# Configuração do banco de dados MySQL
db_config = {
    'host': '',
    'user': '',
    'password': '',
    'database': ''
}

# Conectar ao BD (MySQL)
def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

conexao_db = get_db_connection()

# Configuração do upload de arquivos
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Crie uma instância do chatbot
chatbot = ChatBot('MeuChatBot')
INTENCOES = [
    "/home/edvaldo/DADOS/DEV/workspace/VENVs/ifbot/conversas/saudacoes.json",
    "/home/edvaldo/DADOS/DEV/workspace/VENVs/ifbot/conversas/intencoes.json"
]
# Treinamento do chatbot com o arquivo JSON personalizado
for arquivo_intencoes in INTENCOES:
    with open(arquivo_intencoes, 'r', encoding='utf-8') as file:
        intents_data = json.load(file)

# Conversor de data no formato DD/MM/AAAA para o formato AAAA-MM-DD
def format_date_to_db(date_str):
    try:
        return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None

# Dicionário para armazenar o estado do usuário
user_states = {}

# Sequência de perguntas e chaves
perguntas = {
    1: ['Você escolheu verificar se está cadastrado. Por favor, informe o seu CPF:', 'Por favor, entre com sua data de nascimento:', 'Por favor, entre com seu telefone:', 'Por favor, entre com seu e-mail:'],
    2: ['Você escolheu informar seus dados corretos. Por favor, entre com seu CPF:', 'Os dados estão corretos? (SIM/NÃO)', 'Por favor, entre com seu nome:', 'Por favor, entre com sua data de nascimento:', 'Por favor, entre com seu telefone:', 'Por favor, entre com seu RG:', 'Por favor, entre com seu e-mail:'],
    3: ['Você informou que seus cetificados não estão aparecendo. Por favor, entre com o seu CPF:', 'Por favor, entre_ com seu telefone:', 'Por favor, entre com o nome do evento:', 'Por favor, entre com o ano do evento:']
}

# Rota para o frontend/HTML
@app.route('/')
def index():
    return render_template('index.html')

# Rota para receber as mensagens do usuário
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json['message']
    user_id = request.json.get('user_id')
    # Inicializar estado do usuário
    if user_id not in user_states:
        user_states[user_id] = {'option_id': None, 'step': 0, 'data': {}, 'cpf_found': False}
    user_state = user_states[user_id]
    
    # Verificar se a mensagem do usuário corresponde a uma intenção no JSON
    intent_response = find_intent_response(user_message)
    if intent_response:
        return jsonify({"response": intent_response})
    response = {"response": "Por favor, escolha uma opção para começar o chat."}

    # Processar opções
    if user_state['option_id'] is not None:
        option_id = user_state['option_id']

        if option_id == 1:
            response = option_1(user_message, user_state, user_id)
        elif option_id == 2:
            response = option_2(user_message, user_state, user_id)
        elif option_id == 3:
            response = option_3(user_message, user_state, user_id)
    else:
        response = {"response": "Ainda não sei responder isso. Por favor, escolha uma opção para continuar."}

    # Certifique-se de que a resposta não contém sets
    response = convert_sets_to_lists(response)
    return jsonify(response)

# Função para converter sets em lists
def convert_sets_to_lists(obj):
    if isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, dict):
        return {key: convert_sets_to_lists(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_sets_to_lists(item) for item in obj]
    else:
        return obj

def find_intent_response(user_message):
    user_message = user_message.lower()  # Normaliza a mensagem para minúsculas
    for intent in intents_data['intents']:
        for pattern in intent['patterns']:
            if pattern.lower() in user_message:
                return intent['responses'][0]  # Retorna a primeira resposta correspondente
    return None  # Retorna None se não encontrar uma correspondência

# mostrar apenas as iniciais do nome
def obter_iniciais(nome):
    palavras = nome.split()
    iniciais = [palavra[0].upper() for palavra in palavras]
    return ''.join(iniciais)

# opção 1
def option_1(user_message, user_state, user_id):
    
    if user_state['step'] == 0:  # Solicitar CPF
        user_state['data']['cpf'] = user_message
        response = "Por favor, entre com sua data de nascimento (DD/MM/AAAA):"
        user_state['step'] += 1
        return {"response": response}

    if user_state['step'] == 1:  # Solicitar Data de Nascimento
        user_state['data']['data_nascimento'] = user_message
        cpf = user_state['data']['cpf']
        data_nascimento = format_date_to_db(user_message)

        if not data_nascimento:
            return {"response": f"Formato de data inválido. Por favor, entre com a data de nascimento no formato DD/MM/AAAA:"}

        # Consultar CPF e Data de Nascimento na base de dados
        query = """
            SELECT cpf, nome_completo, data_nascimento 
            FROM participante
            WHERE cpf = %s AND data_nascimento = %s
        """
        cursor = conexao_db.cursor(dictionary=True)
        cursor.execute(query, (cpf, data_nascimento))
        result = cursor.fetchone()
        cursor.close()

        if result:
            user_state['cpf_found'] = True
            user_state['data']['nome_completo'] = result['nome_completo']

            iniciais = obter_iniciais(result['nome_completo'])
            response = f"O CPF e a Data de Nascimento informados correspondem aos encontrados na base de dados e estão associados a {iniciais}."
            

            reset_user_state(user_id)
            return {"response": response}

        response = f"Não foi encontrado um participante cadastrado com os dados informados (CPF e Data de Nascimento).Porém, você poderá informá-los para envio ao coordenador para verificar o cadastro. Por favor, informe seu nome completo:"
        user_state['step'] += 1
        return {"response": response}
        
    if user_state['step'] == 2:  # Solicitar Nome Completo
        user_state['data']['nome_completo'] = user_message
        response = "Por favor, informe o seu telefone:"
        user_state['step'] += 1
        return {"response": response}

    if user_state['step'] == 3:  # Solicitar Telefone
        user_state['data']['telefone'] = user_message
        response = "Por favor, informe o seu e-mail:"
        user_state['step'] += 1
        return {"response": response}

    if user_state['step'] == 4:  # Solicitar E-mail
        user_state['data']['email'] = user_message
        response = "Obrigado! Você informou os seguintes dados:<br><br>"

        for key, value in user_state['data'].items():
            response += f"{key.replace('_', ' ').capitalize()}: {value}<br>"

        response += "<br><br> Anexe seu documento com foto (único arquivo frente e verso) e em seguida pressione o botão Enviar E-mail<br>"

        return {"response": response, "show_upload_buttons": True, "email_data": user_state['data']}

# opção 2
def option_2(user_message, user_state, user_id):
    if user_state['step'] == 0:  # Solicitar CPF
        user_state['data']['cpf'] = user_message

        # Verificar CPF no banco de dados
        query = "SELECT id, nome_completo FROM participante WHERE cpf = %s"
        cursor = conexao_db.cursor(dictionary=True)
        cursor.execute(query, (user_message,))
        result = cursor.fetchone()
        cursor.close()

        if not result:  # CPF não encontrado
            reset_user_state(user_id)
            return {"response": "CPF não encontrado. Sessão encerrada.", "show_upload_buttons": False}

        # CPF encontrado, salvar nome e ID do usuário
        user_state['cpf_found'] = True
        user_state['data']['nome_completo'] = result['nome_completo']
        user_state['data']['user_id'] = result['id']

        response = f"CPF encontrado na base de dados.<br><br> Por favor, informe sua data de nascimento (DD/MM/AAAA):"
        user_state['step'] += 1
        return {"response": response}

    if user_state['step'] == 1:  # Solicitar Data de Nascimento
        user_state['data']['data_nascimento'] = user_message
        cpf = user_state['data']['cpf']
        data_nascimento = format_date_to_db(user_message)

        if not data_nascimento:
            return {"response": "Formato de data inválido. Por favor, entre com a data de nascimento no formato DD/MM/AAAA:", "show_upload_buttons": False}

        # Verificar CPF e DATA_NASCIMENTO no banco de dados
        query = "SELECT id FROM participante WHERE cpf = %s AND data_nascimento = %s"
        cursor = conexao_db.cursor(dictionary=True)
        cursor.execute(query, (cpf, data_nascimento))
        result = cursor.fetchone()
        cursor.close()

        if result:  # CPF e DATA_NASCIMENTO correspondem
            reset_user_state(user_id)
            ini_nome = user_state['data']['nome_completo']
            iniciais = obter_iniciais(ini_nome)

            # Resetar estado do usuário após envio do e-mail
            user_state['option_id'] = None
            user_state['step'] = 0
            user_state['data'] = {}
            user_state['full_responses'] = ''

            op_ini = initial_options()
            return {"response": f"O CPF e a Data de Nascimento informados correspondem aos encontrados na base de dados e estão associados a {iniciais}.","options": op_ini.get_json()["options"]}
            
        response = "A Data de Nascimento não corresponde ao CPF informado.<br><br> Você gostaria de informar os dados corretos para atualização? (SIM/NÃO):"
        user_state['step'] += 1
        return {"response": response}

    if user_state['step'] == 2:  # Atualizar ou não
        if user_message.strip().lower() == "sim":
            user_state['step'] += 1
            response = "Por favor, informe o novo CPF:"
            return {"response": response}
        elif user_message.strip().lower() == "não":
            reset_user_state(user_id)
            return {"response": f"Sessão encerrada. Obrigado!"}
        return {"response": f"Resposta inválida. Deseja atualizar os dados? (SIM/NÃO):"}

    # Coletar informações adicionais
    return informacao_generica(
        user_message,
        user_state,
        required_fields=["cpf", "data_nascimento", "nome_completo", "rg", "telefone", "email"]
    )

# opção 3
def option_3(user_message, user_state, user_id):
    if user_state['step'] == 0:  # Solicitar CPF
        user_state['data']['cpf'] = user_message
        response = "Por favor, informe sua Data de Nascimento (DD/MM/AAAA):"
        user_state['step'] += 1
        return {"response": response}

    if user_state['step'] == 1:  # Solicitar Data de Nascimento
        user_state['data']['data_nascimento'] = user_message
        cpf = user_state['data']['cpf']
        data_nascimento = format_date_to_db(user_message)

        if not data_nascimento:
            return {"response": f"Formato de data inválido. Por favor, entre com a data de nascimento no formato DD/MM/AAAA:"}

        # Verificar CPF e DATA_NASCIMENTO na tabela de usuários
        query_user = """
            SELECT id, nome_completo
            FROM participante
            WHERE cpf = %s AND data_nascimento = %s
        """
        cursor = conexao_db.cursor(dictionary=True)
        cursor.execute(query_user, (cpf, data_nascimento))
        user_result = cursor.fetchone()

        if user_result:  # Usuário encontrado
            user_state['data']['nome_completo'] = user_result['nome_completo']
            user_id = user_result['id']

            # Buscar participações na tabela participacoes
            participations = get_participations_by_user_id(user_id)
            if participations:
                ini_nome = user_state['data']['nome_completo']
                iniciais = obter_iniciais(ini_nome)

                response = f"O CPF e a Data de Nascimento foram encontrados e estão vinculados a {iniciais}.<br><br>Certificados encontrados:<br>"
                for p in participations:
                    response += f"- Evento: Início: {p['data_inicio']}, Fim: {p['data_fim']}<br>"
                reset_user_state(user_id)
                return {"response": response}

            response = "Nenhum certificado encontrado. Por favor, informe o Nome do Evento:"
            user_state['step'] += 2
            return {"response": response}

        response = "CPF e Data de Nascimento não correspondem."
        reset_user_state(user_id)
        return {"response": response}

    return informacao_generica(user_message, user_state, required_fields=["nome_evento", "ano_evento", "telefone", "email"])

# informações genéricas
def informacao_generica(user_message, user_state, required_fields):
    current_field_index = user_state['step'] - 3  # Compensa passos anteriores
    current_field = required_fields[current_field_index]

    # Armazenar a resposta do usuário
    user_state['data'][current_field] = user_message

    # Verificar se há mais campos a serem preenchidos
    if current_field_index + 1 < len(required_fields):
        next_field = required_fields[current_field_index + 1]
        user_state['step'] += 1
        #return jsonify({"response": f"Por favor, informe seu {next_field.replace('_', ' ')}:"})
        return {"response": f"Por favor, informe {next_field.replace('_', ' ')}:"}
    
    # Finalizar a coleta de informações
    response = "Obrigado! <br><br>Aqui estão os dados coletados para atualização:<br><br>"
    for key, value in user_state['data'].items():
        response += f"{key.replace('_', ' ').capitalize()}: {value}<br>"

    response += "<br><br> Prossiga anexando seu documento com foto (único arquivo frente e verso) e em seguida pressione o botão Enviar E-mail<br>"

    return {"response": response, "show_upload_buttons": True, "email_data": user_state['data']}

def get_participations_by_user_id(user_id):
    query = """
        SELECT data_inicio, data_fim, participante_id
        FROM participacao
        WHERE participante_id = %s
    """
    try:
        with conexao_db.cursor(dictionary=True) as cursor:
            cursor.execute(query, (user_id,))
            return cursor.fetchall()  # Retorna uma lista de dicionários com as participações
    except Exception as e:
        print(f"Erro ao buscar participações para o usuário {user_id}: {e}")
        return []

def reset_user_state(user_id):
    user_states[user_id] = {'option_id': None, 'step': 0, 'data': {}, 'cpf_found': False}

# Rota para carregar opções iniciais
@app.route('/initial-options', methods=['GET'])
def initial_options():
    options = [
        {"id": 1, "text": "Verificar se estou cadastrado"},
        {"id": 2, "text": "Estou cadastrado mas com alguns dados incorretos"},
        {"id": 3, "text": "Meus certificados não estão aparecendo"}
    ]
    return jsonify({'options': options})

# Rota para definir a opção selecionada
@app.route('/select-option', methods=['POST'])
def select_option():
    data = request.json
    user_id = data.get('user_id')
    option_id = data['option_id']

    # Reiniciar estado do usuário
    if user_id not in user_states:
        user_states[user_id] = {'option_id': None, 'step': 0, 'data': {}, 'cpf_found': False, 'participations': None}

    user_states[user_id].update({'option_id': option_id, 'step': 0, 'data': {}, 'cpf_found': False, 'participations': None})

    # Primeira pergunta
    first_question = perguntas[option_id][0]

    return jsonify({'response': first_question, 'show_upload_buttons': False})

# Rota para upload de arquivos
@app.route('/upload', methods=['POST'])
def upload():
    user_id = request.form.get('user_id')
    file = request.files['file']
    if file and user_id:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        if user_id in user_states:
            user_states[user_id]['file_path'] = file_path

        return jsonify({'status': 'Arquivo anexado com sucesso!', 'file_path': file_path})

    return jsonify({'status': 'Erro ao enviar arquivo'})

# Rota para enviar o e-mail
@app.route('/send-email', methods=['POST'])
def send_email():
    user_id = request.json.get('user_id')
    user_state = user_states.get(user_id)

    if not user_state:
        return jsonify({'status': 'Usuário não encontrado'})

    email_subject = 'Dados coletados do chatbot'
    email_body = 'Segue dados coletados via chatbot:\n\n'
    for key, value in user_state['data'].items():
        email_body += f'{key.capitalize()}: {value}\n'

    recipient_email = user_state['data'].get('email', 'default_email@gmail.com')

    msg = Message(email_subject, sender='your_email@gmail.com', recipients=[recipient_email])
    msg.body = email_body

    # Anexar o arquivo, se houver
    if user_state['file_path']:
        with app.open_resource(user_state['file_path']) as fp:
            msg.attach(filename=os.path.basename(user_state['file_path']), content_type='application/octet-stream', data=fp.read())

    mail.send(msg)

    # Resetar estado do usuário após envio do e-mail
    user_state['option_id'] = None
    user_state['step'] = 0
    user_state['data'] = {}
    user_state['full_responses'] = ''
    user_state['file_path'] = None

    return jsonify({'status': 'E-mail enviado com sucesso!', 'show_upload_buttons': False, 'show_initial_options': True})

if __name__ == '__main__':
    app.run(debug=True)

