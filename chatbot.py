import time
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# --- Configurações (Substitua pelos seus dados reais da API do WhatsApp) ---
# Em um cenário real, você obterá estes dados do seu App no Meta Developers.
WHATSAPP_API_URL = "https://graph.facebook.com/v19.0/SEU_ID_DO_NUMERO_DE_TELEFONE/messages"
WHATSAPP_ACCESS_TOKEN = "SEU_TOKEN_DE_ACESSO_AQUI"
# --------------------------------------------------------------------------

# Estrutura de dados para armazenar clientes em potencial para follow-up
# Chave: Número de Telefone (ex: '5541987654321'), Valor: Nome (opcional)
prospects_db = {} 

# --- Funções de Envio de Mensagem (Simuladas) ---

def enviar_mensagem(destinatario, tipo_mensagem, dados_mensagem):
    """
    Função para enviar uma mensagem via API do WhatsApp.
    
    Em um ambiente real, esta função faria uma chamada POST para o WHATSAPP_API_URL.
    
    Para o nosso propósito didático, vamos apenas simular o envio.
    """
    if not WHATSAPP_ACCESS_TOKEN or "SEU_TOKEN_DE_ACESSO_AQUI" in WHATSAPP_ACCESS_TOKEN:
        print("\n--- AVISO: O token e URL da API não são reais. Apenas simulando o envio. ---")
    
    print(f"\n[SIMULAÇÃO DE ENVIO] -> Para: {destinatario}")
    print(f"[SIMULAÇÃO DE ENVIO] -> Tipo: {tipo_mensagem}")
    print(f"[SIMULAÇÃO DE ENVIO] -> Conteúdo: {dados_mensagem}")
    
    # Exemplo de como a requisição real seria:
    # headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
    # response = requests.post(WHATSAPP_API_URL, headers=headers, json=dados_mensagem)
    # return response.json()
    
    return {"status": "success", "simulado": True}


def enviar_texto(destinatario, texto):
    """Envia uma mensagem de texto simples."""
    dados_mensagem = {
        "messaging_product": "whatsapp",
        "to": destinatario,
        "type": "text",
        "text": {"body": texto}
    }
    return enviar_mensagem(destinatario, "Texto", dados_mensagem)


def enviar_lista_interativa(destinatario, corpo_msg, titulo_botao, secoes):
    """
    Envia uma mensagem de lista interativa (Menu).
    (Requer o uso de templates na API real, simplificado aqui para demonstração)
    """
    dados_mensagem = {
        "messaging_product": "whatsapp",
        "to": destinatario,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": corpo_msg},
            "action": {
                "button": titulo_botao,
                "sections": secoes
            }
        }
    }
    return enviar_mensagem(destinatario, "Lista Interativa", dados_mensagem)


# --- Lógica do Chatbot ---

def processar_mensagem(remetente, mensagem_recebida):
    """
    Contém a lógica de conversação do chatbot.
    """
    # Converter a mensagem recebida para minúsculas e remover espaços extras
    msg_normalizada = mensagem_recebida.lower().strip()
    
    # --- Ramo Principal: Introdução e Opções Iniciais ---
    
    if msg_normalizada in ["olá", "oi", "bom dia", "começar", "menu"]:
        apresentacao = (
            "🤖 *Bem-vindo(a) à ITAC Desenvolvimento de Soluções Informatizadas!* "
            "Sou seu assistente virtual. Em que posso te ajudar hoje?"
        )
        
        # Estrutura do menu interativo (Botões de Lista):
        secoes = [
            {
                "rows": [
                    {"id": "sou_cliente", "title": "Sou Cliente"},
                    {"id": "nao_sou_cliente", "title": "Ainda Não Sou Cliente"}
                ]
            }
        ]
        
        enviar_lista_interativa(
            remetente,
            apresentacao,
            "Escolha uma Opção",
            secoes
        )
        return
        
    # --- Ramo 1: Sou Cliente ---
    
    elif msg_normalizada in ["sou cliente", "sou_cliente"]:
        mensagem_cliente = (
            "🤝 Olá! Ótimo ter você de volta. O que você precisa? "
            "Como posso melhor atendê-lo(a)?"
        )
        
        secoes_cliente = [
            {
                "rows": [
                    {"id": "suporte_sla", "title": "Entrar em Contato com o Suporte SLA"},
                    {"id": "contratual", "title": "Questões Contratuais"}
                ]
            }
        ]
        
        enviar_lista_interativa(
            remetente,
            mensagem_cliente,
            "Escolha o Assunto",
            secoes_cliente
        )
        return

    # Sub-Ramos do "Sou Cliente"
    
    elif msg_normalizada == "suporte_sla":
        resposta = (
            "🚨 Entendido. Nosso time de Suporte SLA foi notificado. "
            "Por favor, nos envie uma breve descrição do problema, e um técnico "
            "entrará em contato com você em até 1 hora."
        )
        enviar_texto(remetente, resposta)
        return
        
    elif msg_normalizada == "contratual":
        resposta = (
            "📝 Certo. Suas questões contratuais serão encaminhadas para o setor "
            "administrativo. Em horário comercial, um especialista responderá "
            "em até 2 horas. Por favor, especifique o contrato ou o tópico de interesse."
        )
        enviar_texto(remetente, resposta)
        return
        
    # --- Ramo 2: Ainda Não Sou Cliente ---
    
    elif msg_normalizada in ["ainda não sou cliente", "nao_sou_cliente"]:
        # Adiciona o número na lista de prospects para follow-up
        if remetente not in prospects_db:
             prospects_db[remetente] = "Prospect" # Você pode pedir o nome do prospect aqui
             
        resposta = (
            "👋 Sem problemas! Estou feliz em ajudar a iniciar sua jornada. "
            "Nós nos especializamos em soluções de software personalizadas para "
            "pequenos negócios. Um de nossos consultores entrará em contato "
            "com você em breve para entender melhor suas necessidades. "
            "Obrigado pelo seu interesse!"
        )
        enviar_texto(remetente, resposta)

        print(f"\n[DEBUG] Tamanho atual do prospects_db: {len(prospects_db)}")
        print(f"\n[INFO] Número {remetente} adicionado aos prospects para follow-up.")
        return
        
    # --- Resposta Padrão (Fallback) ---
    
    else:
        # Tenta reenviar a mensagem de boas-vindas para reiniciar o fluxo
        enviar_texto(
            remetente, 
            "🤔 Não entendi sua resposta. Por favor, digite *Olá* ou *Menu* para ver as opções, "
            "ou tente selecionar uma das opções interativas anteriores."
        )
        return

# --- Rota do Webhook do Flask ---

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """
    Endpoint que recebe todas as mensagens enviadas para o seu número do WhatsApp.
    
    A API real usa GET para verificar o token e POST para receber mensagens.
    """
    
    # 1. Verificação do Webhook (GET)
    if request.method == 'GET':
        # Esta é a lógica de VERIFICATION no setup da API do WhatsApp
        VERIFY_TOKEN = "seu_token_de_verificacao_aqui" # Defina um token secreto
        
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge"), 200
        else:
            return "Token de verificação inválido", 403

    # 2. Recebimento de Mensagens (POST)
    elif request.method == 'POST':
        data = request.get_json()
        
        # Lógica para extrair a mensagem do payload (altamente simplificado)
        try:
            # Em um cenário real, você teria que navegar na estrutura JSON complexa
            # Ex: data['entry'][0]['changes'][0]['value']['messages'][0]
            
            # SIMULAÇÃO: Assumimos um formato simples para fins de teste
            
            # Remetente: o número de quem enviou (ex: '5541987654321')
            remetente = data.get('from') 
            
            # Mensagem: o texto ou o ID interativo selecionado
            mensagem_recebida = data.get('text')
            
            # Se o remetente e a mensagem existirem, processamos.
            if remetente and mensagem_recebida:
                processar_mensagem(remetente, mensagem_recebida)
            
            # Retorna 200 para a API do WhatsApp, indicando que a mensagem foi recebida
            return jsonify({"status": "recebido"}), 200
            
        except Exception as e:
            # Em caso de falha na extração (ex: mensagens de status), retornamos OK
            print(f"Erro ao processar mensagem recebida: {e}")
            return jsonify({"status": "erro"}), 200


# --- Funcionalidade Adicional: Follow-up via Linha de Comando ---

def enviar_follow_up():
    """
    Envia a mensagem de follow-up para todos os prospects armazenados.
    """
    if not prospects_db:
        print("\n[INFO] Nenhum prospect para follow-up no momento.")
        return
        
    follow_up_msg = (
        "Olá novamente! 👋 Aqui é da ITAC Soluções. "
        "Gostaria de saber se você teve um tempo para pensar em nossas soluções "
        "personalizadas para o seu pequeno negócio. Posso agendar uma "
        "conversa rápida com um consultor esta semana? 💻"
    )
    
    print(f"\n--- Iniciando Follow-up Semanal para {len(prospects_db)} prospects ---")
    for numero, nome in prospects_db.items():
        print(f"Enviando follow-up para: {numero} ({nome})")
        enviar_texto(numero, follow_up_msg)
        # Uma pausa para não sobrecarregar a API
        time.sleep(1) 
        
    print("--- Follow-up Concluído! ---")


# --- Execução Principal do Script ---

if __name__ == '__main__':
    
    import threading

    def iniciar_servidor_flask():
        """Inicia o servidor Flask em uma thread separada."""
        # Host: '0.0.0.0' para ser acessível externamente (necessário para o WhatsApp Webhook)
        # debug=True: recarrega automaticamente o código em mudanças
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

    # Inicia o servidor Flask em uma thread
    # A API do WhatsApp precisa de um endpoint público. Na prática, você usaria 
    # ngrok ou uma plataforma de hospedagem (AWS, Azure, etc.)
    flask_thread = threading.Thread(target=iniciar_servidor_flask)
    flask_thread.daemon = True # Permite que o programa principal termine mesmo com a thread rodando
    flask_thread.start()
    
    print("--- Chatbot Iniciado! ---")
    print("Servidor Webhook Flask rodando em http://0.0.0.0:5000/webhook")
    print("O Flask está rodando em segundo plano. Pressione ENTER para o menu de comandos.")
    
    # Loop da Linha de Comando (CLI) para Follow-up
    while True:
        try:
            input("\nPressione [ENTER] para o Menu CLI...")
            
            print("\n### Menu de Comandos CLI ###")
            print("1. Enviar Follow-up (Follow-up Semanal)")
            print("2. Mostrar Lista de Prospects")
            print("3. Sair")
            
            comando = input("Digite o número da opção: ").strip()
            
            if comando == '1':
                enviar_follow_up()
            elif comando == '2':
                print("\n--- Lista de Prospects para Follow-up ---")
                if prospects_db:
                    for num, nome in prospects_db.items():
                        print(f"- Número: {num}, Nome: {nome}")
                else:
                    print("- Nenhuma entrada na lista.")
            elif comando == '3':
                print("Encerrando o Chatbot...")
                # O loop irá terminar e a aplicação será encerrada
                break
            else:
                print("Comando inválido. Tente novamente.")
                
        except KeyboardInterrupt:
            # Permite encerrar com CTRL+C
            print("\nEncerrando o Chatbot...")
            break
            
    print("Programa encerrado.")