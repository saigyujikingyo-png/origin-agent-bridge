# University of Edinburgh ELM

Public information checked: **2026-09-11**. This is a dated record of university public pages; no personal ELM account was accessed and no API key was used to probe account permissions.

ELM is the university's multi-model service. The reviewed official introduction described free access for students and staff and API-key requests within ELM. This is access to the ELM service, not a transferable token balance for a personal OpenAI, DeepSeek or other provider account. [Official introduction](https://information-services.ed.ac.uk/computing/comms-and-collab/elm/elm-competence-centre/introduction-to-elm)

| Access | Representative models in the reviewed public catalogue |
| --- | --- |
| Web chat | GPT-5.5, GPT-5.4, GPT-5.4-mini/nano and earlier GPT/o series |
| Web chat | Gemini-3.1-flash-lite, Gemini-3.1-pro; locally hosted Llama 3.3 and EuroLLM |
| API | Explicitly listed GPT-5.5/5.5-pro, GPT-5.4/5.4-pro/mini/nano, GPT-5/mini/nano and GPT-4.1; GPT-5.3-codex in the coding category |

The catalogue also described API access to locally hosted and OpenAI models. It **did not explicitly list GPT-5.6 Terra, DeepSeek, GLM or Kimi**. General wording about a model family does not prove a specific account's access. Gemini's web-chat listing does not establish API access to each Gemini model. [Official model catalogue](https://information-services.ed.ac.uk/computing/elm/elm_competence_centre/elm-models-available-through-the-api)

**No universal per-person monthly token allowance, rate limit or unlimited API commitment was verified.** Context-window size is the amount a request can accommodate, not free account quota. Confirm current models, limits and permitted uses through the application page, personal console or ELM team. Commercial API list prices are not treated here as fees students must pay.

To use ELM with Origin Companion, choose an agent supporting a custom model API and local MCP. Configure the ELM-issued key and official endpoint securely in that agent, select an authorised model and connect the local Origin Companion runtime. The university provides [Python/API examples](https://information-services.ed.ac.uk/computing/elm/elm-competence-centre/examples-of-how-to-use-elm-with-python-and-elm-api-key/interacting-with-elm-using-python-and-the-elm-api). Do not assume the ELM web chat itself can install local MCP plugins. Do not put keys in this repository or a sharing package.

Each student or staff member uses their own ELM identity and valid Origin licence. Share the plugin, not university accounts or API keys. Origin Companion's profile configuration does not request quota, enable a model or create another model-inference bill; the chosen host/service meters actual inference.
