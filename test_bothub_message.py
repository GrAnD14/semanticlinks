from openai import OpenAI

client = OpenAI(
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijg1Y2FkOWE4LTcyNjgtNDg3MS04MWUwLTg2NDk3YTY0ZmU1MyIsImlzRGV2ZWxvcGVyIjp0cnVlLCJpYXQiOjE3NDc4NjYwMzAsImV4cCI6MjA2MzQ0MjAzMH0.QWAbUjANDB-gLkBoGTYrj8n7hUDNplVeYG3hfkenpXM",
    base_url="https://bothub.chat/api/v2/openai/v1"
)

# Студент вводит предложение
student_sentence = input("Введите предложение: ")

prompt = (
    "Выдели из следующего предложения ключевые слова и термины. "
    "Верни только список терминов через запятую, без пояснений и лишнего текста.\n"
    f"Предложение: {student_sentence}"
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": prompt}
    ]
)

print("Ключевые слова и термины:")
print(response.choices[0].message.content) 