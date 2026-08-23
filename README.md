# Midgley: LLM-Augmented Unleaded Gas Price Prediction Model

**Midgley** is an AI/ML time-series forecasting engine that predicts wholesale unleaded gasoline prices by fusing **quantitative market technicals** with **unstructured qualitative news event signals** parsed by LLMs.

---

## Key Features

1. **Unstructured LLM Event Extraction (`src/event_analyzer.py`):**
   - Parses energy news, geopolitical headlines, OPEC decisions, and refinery weather disruptions into structured numerical impact scores (*Geopolitical Risk*, *Supply Disruption*, *Demand Sentiment*, *OPEC Action*).
2. **Exponential Memory Decay (`src/feature_engineering.py`):**
   - Applies an exponential decay memory function ($half\text{-}life = 5.0\text{ days}$) to sustain market shock awareness over weeks.
3. **Quantitative Futures Fusion (`src/data_ingestion.py`):**
   - Downloads daily commodity futures (`RB=F` gasoline futures, `CL=F` WTI crude futures, crack spread proxies) using `yfinance`.
4. **Out-of-Time Ablation Study (`src/models.py`):**
   - Evaluates baseline quantitative models against hybrid LLM-augmented models on out-of-time chronological test splits.
5. **Real-Time Counterfactual Scenario Simulator (`main.py`):**
   - Simulates breaking shock events (e.g. *"Category 5 Hurricane approaching Gulf Coast refining complex"*) to quantify immediate price shock premiums.

---

## Installation & Setup

```bash
# Clone the repository
git clone https://github.com/KoshiirRa/midgley.git
cd midgley

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Quickstart

Run the complete pipeline, evaluation, and scenario simulation:

```bash
python main.py
```

To run with live Gemini API scoring (requires `GEMINI_API_KEY` environment variable):

```bash
export GEMINI_API_KEY="your-gemini-api-key"
python main.py --use-llm-api
```

---

## Project Structure

```
.
├── LICENSE                             # Apache 2.0 License
├── README.md                           # Project documentation
├── pyproject.toml / requirements.txt    # Project dependencies
├── main.py                             # Main orchestration script & shock simulator
├── build_notebook.py                   # Script to generate Jupyter Notebook
├── src/
│   ├── data_ingestion.py               # Financial market data fetcher & event dataset
│   ├── event_analyzer.py               # LLM prompt factor scoring & NLP fallback
│   ├── feature_engineering.py          # Technical signals & exponential decay memory fusion
│   └── models.py                       # Chronological train/test split & model ablation
└── notebooks/
    └── gas_price_llm_forecasting.ipynb  # Interactive walkthrough notebook
```

---

## License

Distributed under the **Apache-2.0 License**. See [LICENSE](LICENSE) for details.
