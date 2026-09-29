import json
from openai import OpenAI

PROMPT = """Atua como um conversor de texto para JSON.
A tua tarefa é extrair as informações do "NOVO PEDIDO DO UTILIZADOR" e formatá-las na estrutura JSON especificada.

Regras estritas:
1. Responde APENAS com o objeto JSON final.
2. Não uses marcadores de código Markdown (como ```json ou ```). Não adiciones texto, explicações ou espaços antes ou depois do JSON.
3. Não incluas os dados dos exemplos na resposta. Processa apenas o NOVO PEDIDO.
4. Escreve somente o dia da semana, sem o "feira", por exemplo: "Quarta" em vez de "Quarta-Feira"

Estrutura do JSON:
- TAREFA FIXA com nome como chave (fixed_task): "kind", "day", "start", "end"
- TAREFA OPCIONAL com nome como chave (optional_task): "kind", "domains" (lista com "day", "start", "end"), "durationMin", "durationMax", "peso"

Exemplo de formato esperado (NÃO incluir estes dados na resposta):
{
  "Aula_X": {
    "kind": "fixed_task"
    "day": "Terça",
    "start": "14:00",
    "end": "16:00"
  },
    "Gym": {
    "kind": "optional_task",
    "domains": [
      {
        "day": "Segunda",
        "start": "8:00",
        "end": "21:00"
      },
      {
        "day": "Terça",
        "start": "8:00",
        "end": "21:00"
      }
    ],
    "durationMin": 60,
    "durationMax": 60,
    "peso": 3
  }
}

NOVO PEDIDO DO UTILIZADOR: [PEDIDO DO UTILIZADOR]"""

class TaskExtractor:
    def __init__(self):
        self.client = OpenAI()

    def extract_task(self, user_request: str) -> dict:
        response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": PROMPT},
                          {"role": "user", "content": user_request}
                ]
        )
        return json.loads(response.choices[0].message.content)