# Agent conversațional cu instrumente

Aplicație Python care oferă o interfață de chat Gradio pentru un agent ReAct bazat pe Google Gemini. Agentul poate răspunde la întrebări și poate apela instrumente pentru calcule, dată și oră, vreme și căutări pe web.

## Cerințe

- Python instalat
- O cheie API Google AI pentru Gemini (`GOOGLE_API_KEY`)
- Chei API suplimentare doar pentru funcționalitățile de vreme și căutare web

## Instalare

Din directorul proiectului, creează și activează un mediu virtual, apoi instalează dependențele:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Pe Windows, activează mediul virtual cu:

```powershell
.venv\Scripts\Activate.ps1
```

## Configurare

Creează un fișier `.env` în directorul proiectului. Cheia Gemini este necesară pentru pornirea agentului:

```dotenv
GOOGLE_API_KEY=cheia_ta_google_ai
```

Pentru instrumentele de vreme și căutare web, adaugă și cheile corespunzătoare:

```dotenv
OPEN_WEATHER_API_KEY=cheia_ta_openweathermap
GOOGLE_SEARCH_API_KEY=cheia_ta_google_custom_search
CUSTOM_SEARCH_ENGINE_ID=id_motorului_custom_search
```

`OPEN_WEATHER_API_KEY` este folosit pentru geocodare și vreme. Căutarea web folosește atât `GOOGLE_SEARCH_API_KEY`, cât și `CUSTOM_SEARCH_ENGINE_ID`. Aceste variabile pot lipsi dacă nu folosești instrumentele respective.

## Pornire

```bash
python agent.py
```

Deschide [http://127.0.0.1:7860](http://127.0.0.1:7860) în browser și trimite o întrebare în interfața de chat.

## Instrumente disponibile

- `calculator`: evaluează o expresie matematică.
- `get_current_date_time`: returnează data și ora locală a sistemului.
- `get_location_coordinates`: caută coordonatele unui loc prin OpenWeatherMap.
- `get_current_weather`: returnează vremea curentă pentru coordonate, cu unități metrice, imperiale sau standard.
- `get_web_search_results`: caută pe web și returnează linkuri către rezultate.
- `get_web_page_content`: descarcă și extrage textul paginilor indicate prin URL.

Agentul primește definițiile instrumentelor din `tools/`, validează argumentele cu modelele Pydantic și le expune modelului Gemini. Instrucțiunile pentru agent sunt păstrate ca fișiere YAML în `prompts/` și încărcate de registrul de prompturi.

## Structura proiectului

```text
agent.py                 Punctul de intrare și interfața Gradio
prompts/                 Prompturi YAML și registrul acestora
tools/                   Instrumente, modele de parametri și registrul de instrumente
requirements.txt         Dependențele Python
```

Nu publica fișierul `.env` și nu include cheile API în codul sursă.
