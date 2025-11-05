

from ollama import chat
from ollama import ChatResponse


def main():
    rsp: ChatResponse = chat(model='deepseek-r1:8b', messages=[
  {
    'role': 'user',
    'content': 'Why is the sky blue?',
  },
    ])
    print(rsp['message']['content'])
    # or access fields directly from the response object
    print(rsp.message.content)

if __name__ == "__main__":
    main()