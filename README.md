# AI Research Assistant

Simple setup and usage instructions.

## Setup

1. Install Python 3.12+
2. Install dependencies: `pip install -r requirements.txt .`
3. Install Playwright browser: `playwright install chromium`
4. Set environment variables:
   ```bash
   export EXA_API_KEY=your_exa_api_key
   export GROQ_API_KEY=your_groq_api_key
   ```

## Usage

Run the agent:
```bash
python main.py
```

Enter your research question when prompted.

## Features

- Web search with Exa API
- Content extraction with Crawl4AI
- Safety filtering with Llama Guard
- Multi-step reasoning and synthesis
- Source citations with URLs