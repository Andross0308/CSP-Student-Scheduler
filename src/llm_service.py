import json
from openai import OpenAI

PROMPT = """Atua como um conversor de texto para JSON.
Extrai as informações do pedido do utilizador e formata-as na estrutura JSON especificada.

Regras:
1. Processa apenas o pedido enviado, ignorando os dados do exemplo.
2. Escreve apenas o dia da semana sem "-feira" (ex: "Quarta" em vez de "Quarta-Feira").

Estrutura do JSON:
- TAREFA FIXA com nome como chave: "kind", "day", "start", "end"
- TAREFA OPCIONAL com nome como chave: "kind", "domains" (lista de objetos com "day", "start", "end"), "durationMin", "durationMax", "peso"

Exemplo de formato esperado:
{
  "Aula_X": {
    "kind": "fixed_task",
    "day": "Terça",
    "start": "14:00",
    "end": "16:00"
  },
  "Gym": {
    "kind": "optional_task",
    "domains": [
      {"day": "Segunda", "start": "8:00", "end": "21:00"},
      {"day": "Terça", "start": "8:00", "end": "21:00"}
    ],
    "durationMin": 60,
    "durationMax": 60,
    "weight": 3
  }
}"""

class TaskExtractor:
    def __init__(self, client: OpenAI | None = None):
        self.client = client or OpenAI()

    def extract_task(self, user_request: str) -> dict:
        response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": PROMPT},
                          {"role": "user", "content": user_request}
                ]
        )
        return json.loads(response.choices[0].message.content)