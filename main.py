from src.agent.agent import research_agent
from groq import Groq

client = Groq()


def llama_guard(text: str) -> float:
    completion = client.chat.completions.create(
        model="meta-llama/llama-prompt-guard-2-86m",
        messages=[{"role": "user", "content": text}],
        temperature=1,
        max_completion_tokens=100,
        top_p=1,
        stream=False,
        stop=None,
    )

    return float(completion.choices[0].message.content)


prompt = input("Enter your prompt: ")

if llama_guard(prompt) > 0.6:
    print("Prompt is not safe. Exiting.")
    exit(1)
else:
    result = research_agent.run_sync(prompt)

    print(f"model answer: {result.output}")
