from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# ─────────────────────────────────────────
#  CONFIGURAÇÃO DO NEGÓCIO DO CLIENTE
# ─────────────────────────────────────────

NOME_NEGOCIO = "Gracie Barra Friburgo"
TIPO_NEGOCIO = "academia de jiu-jitsu"
SERVICOS = """
- Aula experimental: gratuita
- Plano mensal: R$340
- Plano trimestral: R$270
- Plano anual: R$200
"""
HORARIOS = "Segunda a sábado, das 6h às 19h"
ENDERECO = "Praça de Olaria - Nova Friburgo"
WHATSAPP_HUMANO = "(22) 99999-0000"

OPENROUTER_API_KEY = "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"
MODELO = "stepfun/step-3.5-flash:free"

SYSTEM_PROMPT = f"""Você é a assistente virtual do {NOME_NEGOCIO}, uma {TIPO_NEGOCIO}.

Seu trabalho é atender clientes via Instagram e WhatsApp de forma simpática e profissional.

SERVIÇOS E PREÇOS:
{SERVICOS}

HORÁRIO DE FUNCIONAMENTO: {HORARIOS}
ENDEREÇO: {ENDERECO}

REGRAS:
- Seja simpática e use linguagem leve (pode usar "oi", "claro!", "com certeza!")
- Responda de forma curta e direta (máximo 3 parágrafos)
- Se o cliente quiser agendar, pergunte: nome, modalidade e dia/horário preferido
- NUNCA invente preços ou informações que não estejam acima
- Se houver reclamação ou situação complexa, encaminhe: {WHATSAPP_HUMANO}
- Quando precisar encaminhar para humano, comece com: [ESCALAR]
"""

# ─────────────────────────────────────────
#  MEMÓRIA DAS CONVERSAS
#  Guarda o histórico por usuário (pelo ID do ManyChat)
# ─────────────────────────────────────────

conversas = {}  # { "usuario_id": [ {role, content}, ... ] }

def obter_historico(usuario_id: str) -> list:
    if usuario_id not in conversas:
        conversas[usuario_id] = []
    return conversas[usuario_id]

def responder(usuario_id: str, mensagem: str) -> str:
    historico = obter_historico(usuario_id)

    historico.append({"role": "user", "content": mensagem})

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODELO,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                *historico
            ]
        }
    )

    dados = response.json()
    texto_resposta = dados["choices"][0]["message"]["content"]

    historico.append({"role": "assistant", "content": texto_resposta})

    # Limita o histórico a 20 mensagens para não crescer demais
    if len(historico) > 20:
        conversas[usuario_id] = historico[-20:]

    return texto_resposta

# ─────────────────────────────────────────
#  ENDPOINTS DO SERVIDOR
# ─────────────────────────────────────────

@app.route("/")
def home():
    return "Agente de atendimento online!"

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Recebe mensagens do ManyChat.
    O ManyChat envia um JSON com os dados do usuário e a mensagem.
    """
    dados = request.json

    # Extrai o ID do usuário e a mensagem
    # (o ManyChat envia nesses campos — ajuste se necessário)
    usuario_id = str(dados.get("subscriber_id") or dados.get("id") or "anonimo")
    mensagem = dados.get("last_input_text") or dados.get("text") or ""

    if not mensagem:
        return jsonify({"messages": [{"type": "text", "text": "Oi! Como posso ajudar?"}]})

    print(f"[{usuario_id}] Cliente: {mensagem}")

    resposta = responder(usuario_id, mensagem)

    print(f"[{usuario_id}] Agente: {resposta}")

    # Retorna no formato que o ManyChat espera
    return jsonify({
        "messages": [
            {
                "type": "text",
                "text": resposta
            }
        ]
    })

@app.route("/webhook", methods=["GET"])
def webhook_verificacao():
    """Verificação do webhook pelo ManyChat."""
    return "OK", 200

# ─────────────────────────────────────────
#  INICIAR O SERVIDOR
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("Servidor iniciando...")
    print("Endpoint do webhook: http://localhost:5000/webhook")
    app.run(host="0.0.0.0", port=5000, debug=True)