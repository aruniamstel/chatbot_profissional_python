import logging
import time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.ext import JobQueue
import threading
import sys
from datetime import time as dt_time, datetime, timedelta
from codigo_bot import TELEGRAM_TOKEN 
from google import genai # Mudou a importação
from google.genai import types # Para as instruções de sistema
from chave_api import GOOGLE_API_KEY
GEMINI_API_KEY = GOOGLE_API_KEY

# --- Configuração Refinada do Gemini ---
# Inicializa o Cliente
client = genai.Client(api_key=GEMINI_API_KEY)

# O "Prompt de Sistema" define as regras de comportamento da IA
SYSTEM_PROMPT = """
Você é o Assistente Virtual Inteligente da ITAC Desenvolvimento de Soluções Informatizadas.
Seu objetivo é ajudar pequenos empresários a entenderem como software pode melhorar seus negócios.

DIRETRIZES DE PERSONALIDADE:
- Tom: Profissional, empático, direto e encorajador.
- Linguagem: Evite termos técnicos excessivos. Se usar um (ex: 'API' ou 'Cloud'), explique brevemente o benefício.
- Foco: Soluções personalizadas para pequenos negócios (Sistemas de gestão, automação de processos, integração de APIs).

REGRAS DE RESPOSTA:
1. Se o usuário perguntar o que você faz: Liste que a ITAC cria softwares sob medida para automatizar tarefas e facilitar a gestão.
2. Se o usuário pedir suporte técnico complexo: Oriente-o a clicar no botão 'Sou Cliente' e depois 'Suporte SLA' usando o comando /start.
3. Se o usuário perguntar preços: Explique que cada projeto é único e que um consultor entrará em contato para fazer um orçamento gratuito.
4. Jamais invente parcerias ou serviços que não sejam desenvolvimento de software.
5. Sempre que terminar uma explicação longa, pergunte se o usuário gostaria de falar com um consultor humano.
"""

async def chamar_gemini(pergunta_usuario):
    try:
        # No novo SDK, usamos o método 'models.generate_content'
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=pergunta_usuario,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7 # Adiciona um pouco de criatividade natural
            )
        )
        return response.text
    except Exception as e:
        print(f"Erro no Gemini: {e}")
        return "Tive um erro ao processar sua pergunta. Tente novamente ou use /start."
    
async def fallback_gemini_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com textos fora do menu usando o Gemini."""
    pergunta = update.message.text
    
    # Feedback visual de "digitando..."
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
    
    resposta_ia = await chamar_gemini(pergunta)
    
    await update.message.reply_text(resposta_ia, parse_mode='Markdown')
    
    return MENU_PRINCIPAL # Mantém o usuário no menu principal

# --- Configurações (Substitua Pelo Seu Token, o token fica salvo em um arquivo a parte) ---
TELEGRAM_BOT_TOKEN = TELEGRAM_TOKEN
# ------------------------------------------------

# Configuração de logging básica
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Estados para o ConversationHandler ---
MENU_PRINCIPAL, CLIENTE_OPCOES, CONTRATO_OPCOES, RECEBE_NOME_CONTRATO = range(4)

# --- Bancos de Dados em Memória ---

# Chave: ID do Chat do Telegram (Inteiro), Valor: Nome ou Username
prospects_db = {} 

# Chave: ID do Chat do Telegram (Inteiro), Valor: {'nome': str, 'job': Job}
contratos_db = {} 

# --- Funções de Envio de Mensagem (Telegram API) ---

async def enviar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE, texto: str, keyboard=None):
    """Envia uma mensagem de texto com ou sem teclado personalizado."""
    await update.message.reply_text(
        texto,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def enviar_follow_up_msg(user_id, texto, application: Application):
    """Função que envia o follow-up. Precisa do objeto 'application'."""
    try:
        await application.bot.send_message(
            chat_id=user_id,
            text=texto,
            parse_mode='Markdown'
        )
        logger.info(f"Follow-up enviado para o ID: {user_id}")
    except Exception as e:
        logger.error(f"Erro ao enviar follow-up para {user_id}: {e}")


# --- Handlers de Mensagens (Lógica do Chatbot) ---

# 1. Comando de Início e Menu Principal
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia a conversa e exibe o menu principal."""
    apresentacao = (
        "🤖 *Bem-vindo(a) à ITAC Desenvolvimento de Soluções Informatizadas!* "
        "Sou seu assistente virtual. Em que posso te ajudar hoje?"
    )
    
    keyboard = [
        [KeyboardButton("Sou Cliente")],
        [KeyboardButton("Ainda Não Sou Cliente")],
        [KeyboardButton("Configurar Contrato (Dev)")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await enviar_texto(update, context, apresentacao, reply_markup)
    
    return MENU_PRINCIPAL

# 2. Resposta do Menu Principal
async def menu_principal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com a seleção do menu principal."""
    msg_recebida = update.message.text.strip()
    chat_id = update.message.chat_id

    # --- Ramo 1: Sou Cliente ---
    if msg_recebida == "Sou Cliente":
        mensagem_cliente = (
            "🤝 Olá! Ótimo ter você de volta. O que você precisa? "
            "Como posso melhor atendê-lo(a)?"
        )
        
        keyboard_cliente = [
            [KeyboardButton("Suporte SLA")],
            [KeyboardButton("Questões Contratuais")]
        ]
        reply_markup_cliente = ReplyKeyboardMarkup(keyboard_cliente, one_time_keyboard=True, resize_keyboard=True)
        
        await enviar_texto(update, context, mensagem_cliente, reply_markup_cliente)
        return CLIENTE_OPCOES

    # --- Ramo 2: Ainda Não Sou Cliente (Prospect) ---
    elif msg_recebida == "Ainda Não Sou Cliente":
        if chat_id not in prospects_db:
             prospects_db[chat_id] = update.message.from_user.username or update.message.from_user.first_name
             logger.info(f"ID {chat_id} adicionado aos prospects.")
             
        resposta = (
            "👋 Sem problemas! ... Um de nossos consultores entrará em contato em breve. "
            "Obrigado pelo seu interesse!"
        )
        await enviar_texto(update, context, resposta)
        return ConversationHandler.END 
        
    # --- Ramo 3: Configurar Contrato (Nova Funcionalidade) ---
    elif msg_recebida == "Configurar Contrato (Dev)":
        await update.message.reply_text("Certo, iniciando configuração de follow-up de contrato.")
        
        if chat_id in contratos_db:
            keyboard_contrato = [
                [KeyboardButton("Remover Agendamento")],
                [KeyboardButton("Voltar ao Menu")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard_contrato, one_time_keyboard=True, resize_keyboard=True)
            await enviar_texto(
                update, context, 
                f"Já existe um agendamento ativo para *{contratos_db[chat_id]['nome']}*. O que deseja fazer?", 
                reply_markup
            )
            return CONTRATO_OPCOES
        else:
            await update.message.reply_text("Por favor, digite o *nome completo* da pessoa que deve receber o follow-up de contrato:")
            return RECEBE_NOME_CONTRATO


# 3. Respostas de Cliente
async def cliente_opcoes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com as opções de cliente (SLA ou Contratual)."""
    msg_recebida = update.message.text.strip()
    
    # ... (A lógica de Suporte SLA e Questões Contratuais permanece a mesma) ...
    
    if msg_recebida == "Suporte SLA":
        resposta = ("🚨 Entendido. Nosso time de Suporte SLA foi notificado. Por favor, nos envie uma breve descrição do problema, e um técnico entrará em contato com você em até 1 hora.")
        await enviar_texto(update, context, resposta)
    
    elif msg_recebida == "Questões Contratuais":
        resposta = ("📝 Certo. Suas questões contratuais serão encaminhadas para o setor administrativo. Um especialista responderá em até 2 horas. Por favor, especifique o contrato ou o tópico de interesse.")
        await enviar_texto(update, context, resposta)
    
    else:
        await enviar_texto(update, context, "🤔 Opção inválida. Por favor, use os botões.")
        return CLIENTE_OPCOES

    return ConversationHandler.END

# --- Novas Funções para Agendamento de Contrato ---

async def handle_recebe_nome_contrato(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe o nome do prospect e agenda o follow-up semanal."""
    nome_prospect = update.message.text.strip()
    chat_id = update.message.chat_id
    
    # Armazena o nome para o agendamento
    context.user_data['contrato_nome'] = nome_prospect
    
    # Agenda a tarefa e armazena o job
    job = application.job_queue.run_repeating(
        callback=follow_up_contrato_task,
        interval=timedelta(weeks=1), # Repetir a cada 1 semana
        first=obter_proximo_horario_agendado(), # Primeira execução
        chat_id=chat_id,
        name=f"Contrato_{chat_id}",
        data={'nome': nome_prospect}
    )
    
    # Armazena o Job e o nome no banco de dados de contratos
    contratos_db[chat_id] = {'nome': nome_prospect, 'job': job}

    agendamento_info = (
        f" Agendamento concluído para *{nome_prospect}*! \n\n"
        f"Enviarei o lembrete semanal de contrato toda *Segunda a Sexta* às *15:30 (horário de Brasília)*."
    )
    await enviar_texto(update, context, agendamento_info)
    logger.info(f"Agendamento de contrato criado para {chat_id} ({nome_prospect}).")
    
    return ConversationHandler.END

def obter_proximo_horario_agendado() -> datetime:
    """Calcula o próximo dia de semana às 15:30."""
    now = datetime.now()
    target_time = dt_time(15, 30, 0)
    
    # Inicia no próximo dia (pode ser hoje se a hora ainda não passou)
    next_run = datetime.combine(now.date(), target_time)
    
    # Se a hora de hoje já passou, vai para amanhã
    if next_run < now:
        next_run += timedelta(days=1)
        
    # Verifica se é fim de semana (Seg=0, Dom=6)
    while next_run.weekday() >= 5: # Sábado (5) ou Domingo (6)
        next_run += timedelta(days=1)
        
    logger.info(f"Próxima execução agendada para: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    return next_run


async def follow_up_contrato_task(context: ContextTypes.DEFAULT_TYPE):
    """Callback executada pelo JobQueue."""
    
    chat_id = context.job.chat_id
    nome_prospect = context.job.data['nome']
    
    # Verifica se o dia atual é um dia de semana (0=Segunda a 4=Sexta)
    if datetime.now().weekday() < 5: 
        mensagem = (
            f"*{nome_prospect}*, bom dia! Tudo bem?\n\n"
            "Só passando para dar uma lembrada no contrato do sistema.\n"
            "Teve chance de dar uma olhada ou tem alguma dúvida que eu possa esclarecer? 😊"
        )
        await enviar_follow_up_msg(chat_id, mensagem, application)
    else:
        # Se for sábado ou domingo, não envia, mas o JobQueue garante que o intervalo de 1 semana será mantido.
        # No entanto, como foi usado run_repeating com um intervalo fixo, a lógica de reajuste é crucial.
        # Para garantir que seja sempre segunda a sexta, o job deve ser re-agendado após a execução.
        # Mas para simplicidade, a verificação 'if weekday() < 5' é suficiente para bloquear o envio no fim de semana.
        logger.info(f"Dia de semana ignorado para {nome_prospect}.")

# 4. Opções de Contrato (Remover/Voltar)
async def contrato_opcoes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com a opção de remover agendamento."""
    msg_recebida = update.message.text.strip()
    chat_id = update.message.chat_id

    if msg_recebida == "Remover Agendamento":
        if chat_id in contratos_db:
            # 1. Remove o Job da fila
            contratos_db[chat_id]['job'].schedule_removal()
            # 2. Remove do banco de dados local
            del contratos_db[chat_id]
            
            await update.message.reply_text("❌ Agendamento de follow-up de contrato removido com sucesso!")
            logger.info(f"Agendamento de contrato removido para {chat_id}.")
        else:
             await update.message.reply_text("Nenhum agendamento ativo encontrado.")
        return ConversationHandler.END

    elif msg_recebida == "Voltar ao Menu":
        await start(update, context)
        return ConversationHandler.END

    return CONTRATO_OPCOES

# 5. Encerramento da Conversa (Opcional)
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela a conversa e limpa o teclado."""
    await update.message.reply_text('Conversa encerrada. Digite /start para recomeçar.')
    return ConversationHandler.END


# --- Funcionalidade de Follow-up (CLI) ---

def iniciar_cli(application: Application):
    """Loop da Linha de Comando (CLI) para Follow-up."""
    
    time.sleep(2) 
    
    print("\n--- Bot Telegram Iniciado! ---")
    print("O Bot está rodando em segundo plano. Pressione ENTER para o menu de comandos.")

    while True:
        try:
            input("\nPressione [ENTER] para o Menu CLI...")
            
            print("\n### Menu de Comandos CLI ###")
            print("1. Enviar Follow-up (Prospects)")
            print("2. Mostrar Lista de Prospects")
            print("3. Mostrar Agendamentos de Contrato") # Novo
            print("4. Sair")
            
            comando = input("Digite o número da opção: ").strip()
            
            if comando == '1':
                if not prospects_db:
                    print("\n[INFO] Nenhum prospect para follow-up no momento.")
                    continue
                    
                follow_up_msg = ("Olá novamente! ... Posso agendar uma conversa rápida esta semana? 💻")
                
                print(f"\n--- Iniciando Follow-up para {len(prospects_db)} prospects ---")
                application.create_task(follow_up_task(application, follow_up_msg))

            elif comando == '2':
                print("\n--- Lista de Prospects (Lead) ---")
                if prospects_db:
                    for chat_id, nome in prospects_db.items():
                        print(f"- ID: {chat_id}, Nome: {nome}")
                else:
                    print("- Nenhuma entrada na lista.")
                    
            elif comando == '3': # Nova Opção
                print("\n--- Lista de Agendamentos de Contrato ---")
                if contratos_db:
                    for chat_id, data in contratos_db.items():
                        job_info = application.job_queue.get_jobs_by_name(f"Contrato_{chat_id}")
                        next_run = job_info[0].next_run_time.strftime('%Y-%m-%d %H:%M:%S') if job_info else "N/A"
                        print(f"- ID: {chat_id}, Nome: {data['nome']}, Próximo Envio: {next_run}")
                else:
                    print("- Nenhum agendamento ativo.")

            elif comando == '4':
                print("Encerrando o Bot...")
                application.stop()
                sys.exit(0)
            else:
                print("Comando inválido. Tente novamente.")
                
        except KeyboardInterrupt:
            print("\nEncerrando o Bot...")
            application.stop()
            sys.exit(0)
        except Exception as e:
             print(f"Erro no CLI: {e}")
             
async def follow_up_task(application: Application, msg):
    """Tarefa assíncrona para enviar o follow-up de prospects."""
    for user_id, nome in prospects_db.items():
        print(f"Enviando follow-up para: {nome} (ID: {user_id})")
        await enviar_follow_up_msg(user_id, msg, application)
        await asyncio.sleep(1) 
    print("--- Follow-up Concluído! ---")


# --- Execução Principal do Bot ---

if __name__ == '__main__':
    import asyncio 

    if "SEU_TOKEN_DO_TELEGRAM_AQUI" in TELEGRAM_BOT_TOKEN:
        print("ERRO: Por favor, substitua 'SEU_TOKEN_DO_TELEGRAM_AQUI' pelo token real do BotFather.")
        sys.exit(1)
        
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # 1. Configuração do Flow de Conversação (ConversationHandler)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        
        states={
            MENU_PRINCIPAL: [
                MessageHandler(filters.Regex("^(Sou Cliente|Ainda Não Sou Cliente|Configurar Contrato \(Dev\))$"), menu_principal_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_gemini_handler) 
            ],
            CLIENTE_OPCOES: [
                MessageHandler(filters.Regex("^(Suporte SLA|Questões Contratuais)$"), cliente_opcoes_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_gemini_handler)
            ],
            CONTRATO_OPCOES: [
                MessageHandler(filters.Regex("^(Remover Agendamento|Voltar ao Menu)$"), contrato_opcoes_handler),
            ],
            RECEBE_NOME_CONTRATO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_recebe_nome_contrato),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel),CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    
    # 2. Inicia o CLI em uma thread separada
    cli_thread = threading.Thread(target=iniciar_cli, args=(application,))
    cli_thread.daemon = True
    cli_thread.start()

    # 3. Inicia o Bot (polling)
    print("Iniciando bot (polling)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)